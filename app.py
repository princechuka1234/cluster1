from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify
from database import db, Customers, Users, Cart, CartItem, Burger, Pizza, Taco, Dessert
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from functools import wraps

# ==============================================================================
# 1. INITIALIZATION & CONFIGURATION
# ==============================================================================
app = Flask(__name__)

app.config['SECRET_KEY'] = 'LONGa23w342q222224'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Paystack Configuration
app.config["PAYSTACK_PUBLIC_KEY"] = "pk_test_e21932b882889bfdd6dff83d25c03c0900061a38"
app.config["PAYSTACK_SECRET_KEY"] = "sk_test_70fd3c240878dcccf9766f459984e96c70547cba"

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Initialize & create tables
db.init_app(app)
with app.app_context():
    db.create_all()

# ==============================================================================
# 2. UTILITY FUNCTIONS & DECORATORS
# ==============================================================================

# Decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))

        if not (current_user.is_admin or current_user.s_admin):
            flash("Access denied. Admins only.", "error")
            return redirect(url_for("index"))

        return f(*args, **kwargs)
    return decorated_function

# Helper function to get cart count
def get_cart_count(user):
    carts = user.cart
    items = carts.items if carts else []
    return len(items)

# ==============================================================================
# 3. AUTHENTICATION ROUTES
# ==============================================================================

# 🔹 User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['usr']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        rep_password = request.form['rep_password']
        phone_len = len(phone)

        # Basic Validation
        if Users.query.filter_by(username=username).first():
            flash("User already exists.", "error")
            return redirect(url_for("register"))
        if Users.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
            return redirect(url_for("register"))
        if any(char.isalpha() for char in phone) or phone_len != 11:
            flash('Phone number is invalid (must be 11 digits and contain only numbers).', 'error')
            return redirect(url_for('register'))
        if not email:
            flash('Email is required!', 'error')
            return redirect(url_for('register'))
        if password != rep_password:
            flash('Password does not match', 'error')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = Users(username=username,phone=phone, email=email, password=hashed_pw)

        db.session.add(new_user)
        db.session.commit()

        # Create cart for new user
        new_cart = Cart(user_id=new_user.id)
        db.session.add(new_cart)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# 🔹 User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Super admin assignment (User with id=1)
            if user.id == 1 and not user.s_admin:
                user.s_admin = True
                db.session.commit()
                
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

    return render_template("sign.html")

# 🔹 Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# ==============================================================================
# 4. PUBLIC & USER ROUTES
# ==============================================================================

@app.route('/')
def index():
    user = current_user if current_user.is_authenticated else None
    cart_c = get_cart_count(user) if user else 0
    username= user.username
            
    return render_template('home.html', cart_c=cart_c, user=user, username=username)

@app.route('/categories')
def categories():
    try:
        user = current_user if current_user.is_authenticated else None
        cart_c = get_cart_count(user) if user else 0

        # products
        burger = Burger.query.order_by(Burger.created_at.desc()).all()
        pizza = Pizza.query.order_by(Pizza.created_at.desc()).all()
        taco = Taco.query.order_by(Taco.created_at.desc()).all()
        dessert = Dessert.query.order_by(Dessert.created_at.desc()).all()

        return render_template('categories.html', cart_c=cart_c, user=user, burger=burger, pizza=pizza, taco=taco, dessert=dessert)

    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for('index'))

# 🔹 Full Cart Page (kept as a direct link/fallback)
@app.route('/cart')
@login_required
def cart():
    user = current_user
    carts = user.cart
    items = carts.items if carts else []
    cart_c = len(items)

    return render_template('cart.html', cart_c=cart_c, items=items, email=user.email, carts=carts)


# 🔹 API endpoint to get cart data (NEW)
@app.route('/api/cart_data')
@login_required
def get_cart_data():
    user = current_user
    carts = user.cart
    
    if not carts:
        return jsonify({'items': [], 'total': 0.0, 'count': 0})

    items_data = []
    for item in carts.items:
        items_data.append({
            'id': item.id,
            'name': item.product_name,
            'price': item.price,
            'quantity': item.quantity,
            'subtotal': round(item.price * item.quantity, 2)
        })

    return jsonify({
        'items': items_data,
        'total': round(carts.total_cost(), 2),
        'count': len(carts.items)
    })

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    product_name = request.form['product_name']
    price = float(request.form['price'])
    quantity = int(request.form['quantity'])

    user = current_user
    carts = user.cart

    # Check if item already exists in cart
    existing_item = CartItem.query.filter_by(cart_id=carts.id, product_name=product_name).first()

    if existing_item:
        existing_item.quantity += quantity
    else:
        new_item = CartItem(cart_id=carts.id, product_name=product_name, price=price, quantity=quantity)
        db.session.add(new_item)

    db.session.commit()
    flash(f"{product_name} added to cart!", "success")
    # Redirect back to the categories page or wherever the user came from
    return redirect(request.referrer or url_for('categories')) 

# 🔹 Remove items from cart (Updated to handle AJAX requests)
@app.route('/remove_item/<int:item_id>', methods=['POST'])
@login_required
def remove_item(item_id):
    user = current_user
    carts = user.cart
    item = CartItem.query.filter_by(id=item_id, cart_id=carts.id).first()

    if item:
        db.session.delete(item)
        db.session.commit()
        
        # Check if the request is AJAX (from the cart overlay)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
             # Return updated cart count for the nav icon
             return jsonify({'status': 'success', 'message': 'Item removed.', 'new_count': len(carts.items)})
             
        flash("Item removed from cart.", "success")
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
             return jsonify({'status': 'error', 'message': 'Item not found.'}), 404
             
        flash("Item not found in your cart.", "error")

    # Fallback redirect for non-AJAX requests
    return redirect(url_for('cart'))

# 🔹 Paystack Payment Initialization
@app.route("/pay", methods=["POST"])
@login_required
def pay():
    user = current_user
    carts = user.cart
    if not carts or carts.total_cost() <= 0:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))
        
    amount_kobo = int(carts.total_cost() * 100)  # Paystack accepts amount in Kobo

    headers = {
        "Authorization": f"Bearer {app.config['PAYSTACK_SECRET_KEY']}",
        "Content-Type": "application/json",
    }
    data = {
        "email": user.email,
        "amount": amount_kobo,
        "callback_url": url_for("payment_callback", _external=True)
    }

    response = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
    res_data = response.json()

    if res_data["status"]:
        return redirect(res_data["data"]["authorization_url"])  # Redirect to Paystack checkout
    else:
        flash("Payment initialization failed. Try again.", "error")
        return redirect(url_for("cart"))

# 🔹 Paystack Payment Callback/Verification
@app.route("/payment/callback")
@login_required
def payment_callback():
    ref = request.args.get("reference")
    if not ref:
        flash("Payment reference missing.", "error")
        return redirect(url_for("cart"))

    headers = {
        "Authorization": f"Bearer {app.config['PAYSTACK_SECRET_KEY']}"
    }
    response = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers)
    res_data = response.json()

    user = current_user
    carts = user.cart

    if res_data["status"] and res_data["data"]["status"] == "success":
        
        # 1. Record the sale in Customers table
        product_entries = [f"{item.product_name} x{item.quantity} (${item.price})" for item in carts.items]
        product_list = ", ".join(product_entries)
        
        new_sales = Customers(
            email=user.email, 
            phone=user.phone, 
            product=product_list, 
            quantity=len(carts.items) # quantity column will store the number of distinct cart items
        )
        db.session.add(new_sales)

        # 2. Clear the cart
        CartItem.query.filter_by(cart_id=carts.id).delete()
        
        db.session.commit()
        flash("Payment successful! Your order has been placed. 🎉", "success")
        
    else:
        flash("Payment failed or cancelled.", "error")

    return redirect(url_for("cart"))

# ==============================================================================
# 5. ADMIN ROUTES
# ==============================================================================

# 🔹 Admin Dashboard
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    user = current_user
    cart_c = get_cart_count(user)

    # Fetch all relevant data
    all_users = Users.query.all()
    all_customers = Customers.query.order_by(Customers.created_at.desc()).all()
    burger = Burger.query.order_by(Burger.created_at.desc()).all()
    pizza = Pizza.query.order_by(Pizza.created_at.desc()).all()
    taco = Taco.query.order_by(Taco.created_at.desc()).all()
    dessert = Dessert.query.order_by(Dessert.created_at.desc()).all()

    # Summary stats
    total_users = len(all_users)
    total_orders = len(all_customers)

    return render_template(
        "dashboard.html",
        cart_c=cart_c,
        user=user,
        users=all_users,
        customers=all_customers,
        total_users=total_users,
        total_orders=total_orders,
        burger=burger,
        pizza=pizza,
        taco=taco,
        dessert=dessert
    )

# 🔹 View Sales/Customers (Can be absorbed into dashboard but kept separate for old code)
@app.route("/customers")
@login_required
@admin_required
def view_customers():
    customers = Customers.query.order_by(Customers.created_at.desc()).all()
    return render_template("customers.html", customers=customers)

# 🔹 Add New Product
@app.route("/add_product", methods=["GET", "POST"])
@login_required
@admin_required
def add_product():
    user = current_user
    if request.method == "POST":
        try:
            image_url = request.form["image_url"]
            name = request.form["name"]
            price = float(request.form["price"])
            category = request.form["category"]
            
            new_product = None
            if category == "Burger":
                new_product = Burger(image=image_url, name=name, price=price)
            elif category == "Pizza":
                new_product = Pizza(image=image_url, name=name, price=price)
            elif category == "Taco":
                new_product = Taco(image=image_url, name=name, price=price)
            elif category == "Dessert":
                new_product = Dessert(image=image_url, name=name, price=price)
            else:
                flash("Invalid product category selected.", "error")
                return redirect(url_for("add_product"))

            db.session.add(new_product)
            db.session.commit()
            flash("Product added successfully!", "success")
            return redirect(url_for("admin_dashboard"))
            
        except ValueError:
            flash("Invalid price entered. Must be a number.", "error")
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding product: {e}", "danger")

    return render_template("add_product.html", user=user)

# 🔹 Delete Product
@app.route("/admin/delete_product/<string:category>/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def delete_product(category, product_id):
    model = None
    if category == "Burger":
        model = Burger
    elif category == "Pizza":
        model = Pizza
    elif category == "Taco":
        model = Taco
    elif category == "Dessert":
        model = Dessert
    
    if model:
        product_to_delete = model.query.get_or_404(product_id)
        try:
            db.session.delete(product_to_delete)
            db.session.commit()
            flash(f"{category} '{product_to_delete.name}' deleted successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting product: {e}", "danger")
    else:
        flash("Invalid product category.", "error")
        
    return redirect(url_for("admin_dashboard"))

# 🔹 Edit User Details/Admin Status
@app.route("/admin/edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    current_admin = current_user
    user_to_edit = Users.query.get_or_404(user_id)

    # Prevent non-super admins from editing the Super Admin
    if user_to_edit.s_admin and not current_admin.s_admin:
        flash("Access denied. Only the Super Admin can edit Super Admin details.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        user_to_edit.phone = request.form["phone"]
        user_to_edit.email = request.form["email"]
        
        # Only Super Admin can change admin status
        if current_admin.s_admin:
            user_to_edit.is_admin = "is_admin" in request.form
            
        try:
            db.session.commit()
            flash(f"User '{user_to_edit.email}' info updated successfully!", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating user: {e}", "danger")

    return render_template("edit_user.html", user=current_admin, users=user_to_edit) # Note: passing user_to_edit as 'users' for template compatibility

# 🔹 Demote Admin
@app.route("/admin/demote_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def demote_user(user_id):
    if user_id == 1:
        flash("Cannot demote the Super Admin.", "error")
        return redirect(url_for("admin_dashboard"))

    user_to_demote = Users.query.get_or_404(user_id)
    current_admin = current_user
    
    # Only Super Admin can demote
    if not current_admin.s_admin:
        flash("Only the Super Admin can change administrative roles.", "error")
        return redirect(url_for("admin_dashboard"))
    
    if user_to_demote.is_admin:
        try:
            user_to_demote.is_admin = False
            db.session.commit()
            flash(f"User '{user_to_demote.email}' demoted successfully (admin privileges removed).", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error demoting user: {e}", "danger")
    else:
        flash(f"User '{user_to_demote.email}' is not an admin.", "warning")
        
    return redirect(url_for("admin_dashboard"))

# 🔹 Delete User
@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == 1:
        flash("Cannot delete the Super Admin user.", "error")
        return redirect(url_for("admin_dashboard"))

    current_admin = current_user
    if not current_admin.s_admin:
        flash("Only the Super Admin can delete users.", "error")
        return redirect(url_for("admin_dashboard"))

    user_to_delete = Users.query.get_or_404(user_id)
    
    try:
        # Delete associated CartItems and the Cart first
        if user_to_delete.cart:
            CartItem.query.filter_by(cart_id=user_to_delete.cart.id).delete()
            db.session.delete(user_to_delete.cart)

        # Delete the User
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"User '{user_to_delete.email}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting user: {e}", "danger")
        
    return redirect(url_for("admin_dashboard"))

# ==============================================================================
# 6. APPLICATION RUN
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True)
