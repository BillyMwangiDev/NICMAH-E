/**
 * NICMAH - Main JavaScript
 * Compatible with Tailwind CDN - No Bootstrap Dependencies
 * Handles cart functionality, alerts, modals, and general interactivity
 */

/* ============================================
   Modal System (Tailwind-based, no Bootstrap)
   ============================================ */
class Modal {
    constructor(elementId) {
        this.element = document.getElementById(elementId);
        if (!this.element) {
            console.warn(`Modal element with id "${elementId}" not found`);
            return;
        }
        this.isVisible = false;
        this.init();
    }

    init() {
        // Add close button handlers
        const closeButtons = this.element.querySelectorAll('[data-dismiss="modal"], .btn-close, [data-bs-dismiss="modal"]');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.hide());
        });

        // Close on overlay click
        this.element.addEventListener('click', (e) => {
            if (e.target === this.element) {
                this.hide();
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible) {
                this.hide();
            }
        });
    }

    show() {
        if (!this.element) return;
        this.element.classList.remove('hidden');
        this.element.classList.add('show');
        this.isVisible = true;
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
        this.element.classList.remove('show');
        this.isVisible = false;
        document.body.style.overflow = ''; // Restore scrolling
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
}

// Bootstrap-compatible Modal class for existing code
window.bootstrap = window.bootstrap || {};
window.bootstrap.Modal = function(element) {
    // Handle both element and element ID
    const el = typeof element === 'string' ? document.getElementById(element) : element;
    if (!el) {
        console.warn('Modal element not found');
        return null;
    }

    // Convert Bootstrap modal to our modal system
    const modal = new Modal(el.id || 'previewModal');
    
    return {
        show: () => modal.show(),
        hide: () => modal.hide(),
        toggle: () => modal.toggle()
    };
};

/* ============================================
   Cart Functionality
   ============================================ */
class Cart {
    constructor() {
        this.items = JSON.parse(localStorage.getItem('cart')) || [];
        // Normalize IDs to strings on load to avoid type mismatch
        this.items = this.items.map(item => ({
            ...item,
            id: String(item.id)
        }));
        this.updateCartDisplay();
    }

    addItem(productId, name, price, quantity = 1) {
        // Validate inputs
        if (!productId || !name || !price) {
            console.error('Invalid product data:', { productId, name, price });
            this.showAlert('Error: Invalid product data', 'error');
            return;
        }
        const normalizedId = String(productId);
        const existingItem = this.items.find(item => String(item.id) === normalizedId);

        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            this.items.push({
                id: normalizedId,
                name: name,
                price: parseFloat(price),
                quantity: quantity
            });
        }
        this.saveCart();
        this.updateCartDisplay();
        this.showAlert('Product added to cart!', 'success');
    }

    removeItem(productId) {
        const normalizedId = String(productId);
        console.log('removeItem called with productId:', normalizedId);
        console.log('Cart items before removal:', this.items);
        if (!normalizedId) {
            console.error('removeItem: productId is required');
            this.showAlert('Error: Product ID is required', 'error');
            return false;
        }
        const itemToRemove = this.items.find(item => String(item.id) === normalizedId);
        if (!itemToRemove) {
            console.error('removeItem: Item not found with ID:', normalizedId);
            this.showAlert('Error: Item not found in cart', 'error');
            return false;
        }
        const itemName = itemToRemove.name;
        const itemElement = document.querySelector(`[data-product-id="${normalizedId}"]`);
        if (itemElement) {
            itemElement.style.animation = 'fadeOut 0.3s ease-out forwards';
            itemElement.style.transform = 'translateX(20px)';
            itemElement.style.opacity = '0';
            setTimeout(() => {
                const originalLength = this.items.length;
                this.items = this.items.filter(item => String(item.id) !== normalizedId);
                if (this.items.length === originalLength) {
                    console.error('removeItem: Item was not removed');
                    this.showAlert('Error: Failed to remove item', 'error');
                    return false;
                }
                console.log('Cart items after removal:', this.items);
                this.saveCart();
                this.updateCartDisplay();
                this.showAlert(`${itemName} removed from cart!`, 'success');
                console.log('removeItem completed successfully with animation');
                return true;
            }, 300);
        } else {
            const originalLength = this.items.length;
            this.items = this.items.filter(item => String(item.id) !== normalizedId);
            if (this.items.length === originalLength) {
                console.error('removeItem: Item was not removed');
                this.showAlert('Error: Failed to remove item', 'error');
                return false;
            }
            console.log('Cart items after removal:', this.items);
            this.saveCart();
            this.updateCartDisplay();
            this.showAlert(`${itemName} removed from cart!`, 'success');
            console.log('removeItem completed successfully');
            return true;
        }
    }

    updateQuantity(productId, quantity) {
        const normalizedId = String(productId);
        const item = this.items.find(item => String(item.id) === normalizedId);
        if (item) {
            item.quantity = parseInt(quantity);
            if (item.quantity <= 0) {
                this.removeItem(normalizedId);
            } else {
                this.saveCart();
                this.updateCartDisplay();
            }
        } else {
            console.error('updateQuantity: Item not found with ID:', normalizedId);
            this.showAlert('Error: Item not found in cart', 'error');
        }
    }

    clearCart() {
        this.items = [];
        this.saveCart();
        this.updateCartDisplay();
        this.showAlert('Cart cleared!', 'info');
    }

    // Clean cart by removing invalid items
    cleanCart() {
        const before = this.items.length;
        this.items = this.items.filter(item => 
            item && item.name && item.price && item.name !== 'undefined' && item.name !== 'null'
        );
        const after = this.items.length;
        if (after !== before) {
            this.saveCart();
            this.updateCartDisplay();
            // Intentionally no alert to avoid noisy notifications on page load
        }
    }

    getTotal() {
        return this.items.reduce((total, item) => total + (item.price * item.quantity), 0);
    }

    getItemCount() {
        return this.items.reduce((count, item) => count + item.quantity, 0);
    }

    saveCart() {
        // Ensure we store normalized string IDs
        const normalized = this.items.map(item => ({ ...item, id: String(item.id) }));
        localStorage.setItem('cart', JSON.stringify(normalized));
    }

    updateCartDisplay() {
        const cartCount = document.getElementById('cart-count');
        const cartTotal = document.getElementById('cart-total');
        
        if (cartCount) {
            cartCount.textContent = this.getItemCount();
        }
        
        if (cartTotal) {
            cartTotal.textContent = `KSh ${this.getTotal().toFixed(2)}`;
        }
        
        // Update cart dropdown
        this.updateCartDropdown();
        
        // Trigger cart updated event
        window.dispatchEvent(new CustomEvent('cartUpdated'));
    }

    updateCartDropdown() {
        const cartItemsContainer = document.getElementById('cart-items');
        if (!cartItemsContainer) return;
        
        if (this.items.length === 0) {
            cartItemsContainer.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    <i class="fas fa-shopping-cart text-2xl mb-2"></i>
                    <p>Your cart is empty</p>
                </div>
            `;
            return;
        }
        
        let itemsHtml = '';
        this.items.forEach(item => {
            // Validate item data and skip invalid items
            if (!item.name || !item.price || item.name === 'undefined') {
                console.error('Invalid cart item:', item);
                return;
            }
            
            itemsHtml += `
                <div class="p-3 border-b border-gray-100 last:border-b-0">
                    <div class="flex items-center space-x-3">
                        <div class="flex-1">
                            <p class="font-medium text-gray-800 text-sm">${this.escapeHtml(item.name)}</p>
                            <p class="text-xs text-gray-600">Qty: ${item.quantity}</p>
                        </div>
                        <div class="text-right">
                            <span class="font-semibold text-agro-green text-sm">KSh ${(item.price * item.quantity).toFixed(2)}</span>
                            <button onclick="window.cart.removeItem('${this.escapeHtml(item.id)}')" class="ml-2 text-xs text-red-500 hover:text-red-700">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        cartItemsContainer.innerHTML = itemsHtml;
        
        // Force refresh cart page if we're on it
        if (window.location.pathname.includes('/cart/')) {
            setTimeout(() => {
                if (typeof displayCart === 'function') {
                    displayCart();
                }
            }, 100);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showAlert(message, type = 'info') {
        const alertDiv = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        alertDiv.className = `${bgColor} text-white px-6 py-3 rounded-lg shadow-lg mb-2 fixed top-4 right-4 z-50 transform translate-x-full transition-transform duration-300`;
        alertDiv.innerHTML = `
            <div class="flex items-center justify-between">
                <span>${this.escapeHtml(message)}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Animate in
        setTimeout(() => {
            alertDiv.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.add('translate-x-full');
            setTimeout(() => {
                if (document.body.contains(alertDiv)) {
                    document.body.removeChild(alertDiv);
                }
            }, 300);
        }, 5000);
    }
}

/* ============================================
   WhatsApp Checkout
   ============================================ */
function checkoutViaWhatsApp() {
    if (!window.cart || window.cart.items.length === 0) {
        if (window.cart) {
            window.cart.showAlert('Your cart is empty!', 'warning');
        } else {
            alert('Your cart is empty!');
        }
        return;
    }

    const phoneNumber = '+254740368581';
    const orderDetails = generateOrderMessage();
    const encodedMessage = encodeURIComponent(orderDetails);
    const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
    
    window.open(whatsappUrl, '_blank');
}

function generateOrderMessage() {
    if (!window.cart) return '';
    
    const items = window.cart.items.map(item => 
        `• ${item.name} - Qty: ${item.quantity} - KSh ${(item.price * item.quantity).toFixed(2)}`
    ).join('\n');
    
    const total = window.cart.getTotal();
    const itemCount = window.cart.getItemCount();
    
    return `Hello! I would like to place an order from NICMAH:

${items}

Total Items: ${itemCount}
Total Amount: KSh ${total.toFixed(2)}

Please confirm my order and arrange delivery. Thank you!`;
}

/* ============================================
   Utility Functions
   ============================================ */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: 'KES'
    }).format(amount);
}

function showLoading(element) {
    if (element) {
        element.innerHTML = '<div class="loading-spinner"></div>';
        element.disabled = true;
    }
}

function hideLoading(element, originalText) {
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

function performSearch(query) {
    if (query.length < 2) return;
    
    // This will be implemented with actual search logic
    console.log('Searching for:', query);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/* ============================================
   Scroll Animation Observer
   ============================================ */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    if (animatedElements.length === 0) return;
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    animatedElements.forEach(el => observer.observe(el));
}

/* ============================================
   Initialize on DOM Ready
   ============================================ */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart
    window.cart = new Cart();
    window.cart.cleanCart();
    
    // Debug: Log cart state
    console.log('Cart initialized:', window.cart);
    console.log('Cart items:', window.cart.items);
    console.log('Cart count:', window.cart.getItemCount());
    
    // Trigger a custom event when cart is ready
    window.dispatchEvent(new CustomEvent('cartReady'));
    
    // Initialize scroll animations
    initScrollAnimations();
    
    // Initialize all modals on the page
    const modalElements = document.querySelectorAll('.modal, .modal-overlay');
    modalElements.forEach(modalEl => {
        if (modalEl.id) {
            new Modal(modalEl.id);
        }
    });
    
    // Handle Bootstrap data attributes for modals
    document.querySelectorAll('[data-bs-toggle="modal"], [data-toggle="modal"]').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-bs-target') || this.getAttribute('data-target');
            if (targetId) {
                const modalId = targetId.replace('#', '');
                const modal = new Modal(modalId);
                modal.show();
            }
        });
    });
});

/* ============================================
   CSRF Token Utilities
   ============================================ */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFToken() {
    // Try meta tag first (more reliable)
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        const token = metaTag.getAttribute('content');
        if (token && token.length > 0) {
            return token;
        }
    }
    
    // Fallback to cookie
    return getCookie('csrftoken');
}

/* ============================================
   Export Functions for Global Use
   ============================================ */
window.NICMAH = {
    Cart: Cart,
    Modal: Modal,
    checkoutViaWhatsApp: checkoutViaWhatsApp,
    formatCurrency: formatCurrency,
    showLoading: showLoading,
    hideLoading: hideLoading,
    validateForm: validateForm,
    performSearch: performSearch,
    debounce: debounce,
    getCSRFToken: getCSRFToken,
    getCookie: getCookie
};

/* ============================================
   Debug Console Commands
   ============================================ */
window.clearCartForTesting = function() {
    if (window.cart) {
        window.cart.clearCart();
        localStorage.removeItem('cart');
        console.log('Cart cleared for testing!');
        alert('Cart cleared for fresh testing!');
    }
};

window.refreshCartPage = function() {
    if (window.location.pathname.includes('/cart/')) {
        if (typeof displayCart === 'function') {
            displayCart();
        } else {
            location.reload();
        }
    }
};

window.clearCorruptedCart = function() {
    if (window.cart) {
        window.cart.items = window.cart.items.filter(item => 
            item && item.name && item.name !== 'undefined' && item.name !== 'null'
        );
        window.cart.saveCart();
        window.cart.updateCartDisplay();
        console.log('Corrupted cart data cleared!');
        alert('Corrupted cart data cleared!');
    }
};

window.addTestItems = function() {
    if (window.cart) {
        window.cart.addItem('test-1', 'Cattle Dewormer', 28.75);
        window.cart.addItem('test-2', 'Pig Feed Mix', 35.00);
        window.cart.addItem('test-3', 'Premium Seeds', 24.99);
        console.log('Test items added to cart!');
        alert('Test items added to cart!');
    }
};

// Log available console commands
console.log('NICMAH - JavaScript Loaded');
console.log('Available commands:');
console.log('- window.clearCartForTesting() - Clear cart for testing');
console.log('- window.clearCorruptedCart() - Clear corrupted cart data');
console.log('- window.addTestItems() - Add test items to cart');
console.log('- window.refreshCartPage() - Force refresh cart page');
console.log('- window.cart.clearCart() - Clear cart');
console.log('- window.cart.cleanCart() - Clean invalid items');
console.log('- window.cart.items - View cart items');
console.log('- window.cart.getItemCount() - Get item count');
console.log('- window.cart.getTotal() - Get total');
