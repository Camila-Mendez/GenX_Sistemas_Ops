from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
import random


# Simulación de usuarios
# Los "users" son los que van al dashboard
# Los "shoppers" son los que van a la tienda
users = {
    'Camila': {
        'password': generate_password_hash('password1'),
        'role': 'user'
    },
    'Mani': {
        'password': generate_password_hash('password2'),
        'role': 'shopper'
    }
}
#Simulación de shopping cart
#Primero se definen los productos
#Después se define el cart en sesión
PRODUCTS = {
    'premium_tiquicia': {
        'name': 'Premium Tiquicia',
        'price': 18.50
    },
    'hacienda_araya': {
        'name': 'Hacienda Araya',
        'price': 20.50
    },
    'finca_el_alto': {
        'name': 'Finca El Alto',
        'price': 15.50
    },
    'premium_coffee_blend': {
        'name': 'Premium Coffee Blend',
        'price': 18.50
    },
    "finca_dota": {
        "name": "Finca Dota",
        "price": 15.30,
    },
    "finca_tarrazu": {
        "name": "Finca Tarrazú",
        "price": 16.50,
    }

}

# ---------------------------------------------------------
#  PUBLIC ROUTES
# ---------------------------------------------------------

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/aboutus')
def aboutus():
    return render_template("aboutus.html")


@app.route('/contactsales')
def contactsales():
    return render_template("contactsales.html")

# ---------------------------------------------------------
# LOGIN (two types)
# ---------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # user or shopper

        # 1. Validación básica
        if username not in users:
            return render_template("login.html", error="Invalid credentials")

        db_user = users[username]

        if not check_password_hash(db_user["password"], password):
            return render_template("login.html", error="Invalid credentials")

        # 2. Validar rol
        if db_user["role"] != role:
            # e.g. user tries to log as shopper
            return render_template("login.html", error="Incorrect login type")

        # 3. Guardar sesión
        session['username'] = username
        session['role'] = db_user["role"]

        # 4. Redirección según tipo
        if role == "shopper":
            return redirect(url_for('shop'))
        else:
            return redirect(url_for('dashboard'))

    return render_template('login.html')


# ---------------------------------------------------------
# REGISTER (only shoppers)
# ---------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username in users:
            return render_template("register.html", error="Username already exists")

        # Crear shopper
        users[username] = {
            "password": generate_password_hash(password),
            "role": "shopper"
        }

        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------------------------------------------------
# USER DASHBOARD (ONLY users)
# ---------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'user':
        return redirect(url_for('shop'))

    return render_template("dashboard.html", username=session['username'])


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))


# ---------------------------------------------------------
# SHOP (shoppers ONLY)
# ---------------------------------------------------------

@app.route('/shop')
def shop():
    if 'username' not in session or session.get('role') != 'shopper':
        return redirect(url_for('login'))

    session.setdefault('cart', {})
    return render_template("shop.html")

# ---------------------------------------------------------
# CART
# ---------------------------------------------------------

@app.route('/add-to-cart/<product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if product_id in cart:
        cart[product_id]['qty'] += 1
    else:
        product = PRODUCTS.get(product_id)
        if not product:
            return redirect(url_for('shop'))

        cart[product_id] = {
            'name': product['name'],
            'price': product['price'],
            'qty': 1
        }

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('shop'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['qty'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total)

@app.route('/remove-from-cart/<product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))

@app.route('/update-cart/<product_id>/<action>')
def update_cart(product_id, action):
    cart = session.get('cart', {})

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['qty'] += 1

        elif action == 'decrease':
            cart[product_id]['qty'] -= 1
            if cart[product_id]['qty'] <= 0:
                del cart[product_id]

        session['cart'] = cart
        session.modified = True

    return redirect(url_for('cart'))

# ---------------------------------------------------------
# CHECKOUT
# ---------------------------------------------------------

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'username' not in session or session.get('role') != 'shopper':
        return redirect(url_for('login'))

    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('shop'))

    total = sum(item['price'] * item['qty'] for item in cart.values())

    if request.method == 'POST':
        # datos simulados
        order = {
            'customer': session['username'],
            'address': request.form['address'],
            'country': request.form['country'],
            'total': total
        }
        session['order'] = order
        return redirect(url_for('payment'))

    return render_template('checkout.html', cart=cart, total=total)



@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'order' not in session:
        return redirect(url_for('shop'))

    if request.method == 'POST':
        # simulación de pasarela
        approved = random.choice([True, True, False])  # 66% éxito

        if approved:
            return redirect(url_for('payment_success'))
        else:
            return redirect(url_for('payment_failed'))

    return render_template('payment.html', order=session['order'])

@app.route('/payment-success')
def payment_success():
    order = session.get('order')

    # aquí en el futuro → guardar en BD
    session.pop('cart', None)
    session.pop('order', None)

    return render_template('payment_success.html', order=order)
