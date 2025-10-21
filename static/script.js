// script.js - Add interactivity to Cluster 1 landing page

document.addEventListener('DOMContentLoaded', function () {
    // Loading animation
    const loaderWrapper = document.querySelector('.loader-wrapper');
    if (loaderWrapper) {
        setTimeout(() => {
            loaderWrapper.classList.add('hidden');
        }, 3000); // Hides the loader after 3 seconds
    }

    updateCartCount();

    // Smooth scroll for nav links
    document.querySelectorAll('nav a[href^="#"]').forEach(link => {
        link.addEventListener('click', function (e) {
            // Check if the link is a normal link or a scroll link
            if (this.getAttribute('href').length > 1) {
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    // Add to cart button functionality
    document.querySelectorAll('.add-to-cart').forEach(btn => {
        btn.addEventListener('click', function () {
            const productName = this.closest('.product-card').querySelector('.name').textContent;
            showToast(`${productName} has been added to your cart!`);

            // add structured item to cart
            const priceText = this.closest('.product-card').querySelector('.price').textContent || '';
            const price = parseFloat(priceText.replace(/[^0-9\.]/g, '')) || 0;
            const item = {
                id: Date.now().toString(),
                name: productName,
                price: price,
                qty: 1
            };
            addItemToCart(item);

            const originalText = btn.textContent;
            btn.textContent = 'Added!';
            btn.disabled = true;
            btn.style.background = '#4caf50';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
                btn.style.background = '';
            }, 1200);
        });
    });

    // Wire cart UI actions
    const cartIcon = document.querySelector('.cart-icon');
    if (cartIcon) {
        cartIcon.addEventListener('click', function (e) {
            e.preventDefault();
            toggleCartModal(true);
        });
    }

    const cartClose = document.getElementById('cart-close');
    if (cartClose) cartClose.addEventListener('click', () => toggleCartModal(false));

    const clearCartBtn = document.getElementById('clear-cart');
    if (clearCartBtn) clearCartBtn.addEventListener('click', () => { clearCart(); renderCart(); });

    // initial render
    renderCart();

    // Contact form fake submit
    const contactForm = document.querySelector('#contact form');
    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();
            alert('Thank you for contacting us! We will get back to you soon.');
            contactForm.reset();
        });
    }

    // Newsletter form UX
    const newsletterForm = document.getElementById('newsletter-form');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const email = newsletterForm.querySelector('input[type="email"]').value;
            if (email) {
                alert('Subscribed! Thank you for joining our newsletter.');
                newsletterForm.reset();
            }
        });
    }
    // Hamburger menu toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('ul.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function () {
            const isOpen = navLinks.classList.toggle('open');
            navToggle.classList.toggle('open', isOpen);
            navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
        // Close menu on link click (mobile UX)
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function () {
                navLinks.classList.remove('open');
                navToggle.classList.remove('open');
                navToggle.setAttribute('aria-expanded', 'false');
            });
        });
    }
});

function showToast(message) {
    const toast = document.getElementById('toast-notification');
    if (toast) {
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

function updateCartCount() {
    const cartCount = localStorage.getItem('cartCount') || '0';
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        cartCountElement.textContent = cartCount;
    }
}

/* Cart helpers: store array of items under 'cartItems' */
function getCartItems() {
    try {
        return JSON.parse(localStorage.getItem('cartItems') || '[]');
    } catch (e) {
        return [];
    }
}

function setCartItems(items) {
    localStorage.setItem('cartItems', JSON.stringify(items));
    const totalQty = items.reduce((s, it) => s + (it.qty || 0), 0);
    localStorage.setItem('cartCount', String(totalQty));
    updateCartCount();
}

function addItemToCart(newItem) {
    const items = getCartItems();
    // try to merge by name
    const existing = items.find(i => i.name === newItem.name);
    if (existing) {
        existing.qty = (existing.qty || 0) + 1;
    } else {
        items.push(newItem);
    }
    setCartItems(items);
    renderCart();
}

function removeItemFromCart(id) {
    let items = getCartItems();
    items = items.filter(i => i.id !== id);
    setCartItems(items);
    renderCart();
}

function clearCart() {
    localStorage.removeItem('cartItems');
    localStorage.setItem('cartCount', '0');
    updateCartCount();
    toggleCartModal(false);
}

function formatCurrency(n) {
    return '$' + Number(n || 0).toFixed(2);
}

function renderCart() {
    const container = document.getElementById('cart-items');
    const subtotalEl = document.getElementById('cart-subtotal');
    const items = getCartItems();
    if (!container) return;
    container.innerHTML = '';
    if (items.length === 0) {
        container.innerHTML = '<div class="empty-cart">Your cart is empty.</div>';
        if (subtotalEl) subtotalEl.textContent = formatCurrency(0);
        return;
    }
    let subtotal = 0;
    items.forEach(it => {
        const row = document.createElement('div');
        row.className = 'cart-item';
        row.innerHTML = `
            <div class="ci-name">${escapeHtml(it.name)}</div>
            <div class="ci-qty">x${it.qty || 1}</div>
            <div class="ci-price">${formatCurrency((it.price || 0) * (it.qty || 1))}</div>
            <button class="btn-muted btn-remove" data-id="${it.id}">Remove</button>
        `;
        container.appendChild(row);
        subtotal += (it.price || 0) * (it.qty || 1);
    });
    if (subtotalEl) subtotalEl.textContent = formatCurrency(subtotal);

    // attach remove handlers
    container.querySelectorAll('.btn-remove').forEach(b => {
        b.addEventListener('click', function () {
            const id = this.getAttribute('data-id');
            removeItemFromCart(id);
        });
    });
}

function toggleCartModal(show) {
    const modal = document.getElementById('cart-modal');
    if (!modal) return;
    if (show) {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        renderCart();
    } else {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    }
}

function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
