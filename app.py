import os
import re
import pokebase as pb
import requests

#from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from functools import wraps
from flask_sqlalchemy import SQLAlchemy

##################################################################################################
# Application configuration
app = Flask(__name__)

# TODO: Security configuration
#from flask_talisman import Talisman
#talisman = Talisman(app, content_security_policy=None)


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'site.db')
db = SQLAlchemy(app)


# Database class-models
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# TODO: app.config["SECRET_KEY"] = "your_secret_key_here"
Session(app)

##################################################################################################
# Set the Pokebase cache location
pb.cache.set_cache('C:/Users/ricar/projects/cs50-final-project/.cache/pokebase')

# Global cache for Pokemon sprites and data
pokemon_sprites_cache = [pb.SpriteResource('pokemon', pokemon_id) for pokemon_id in range(1, 494)]
pokemon_data_cache = []

def fetch_pokemon_details(url):
    # Send a GET request to the PokeAPI
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        pokemon_details = response.json()

        # Extract types, abilities, stats, etc.
        types = [type_data['type']['name'] for type_data in pokemon_details['types']]
        abilities = [ability_data['ability']['name'] for ability_data in pokemon_details['abilities']]
        stats = [{'name': stat_data['stat']['name'], 'value': stat_data['base_stat']} for stat_data in pokemon_details['stats']]
        
        # Create the Pokemon data dictionary
        pokemon_data = {
            'id': pokemon_details['id'],
            'name': pokemon_details['name'],
            'height': pokemon_details['height'],
            'weight': pokemon_details['weight'],
            'types': types,
            'abilities': abilities,
            'stats': stats,
            # TODO: Add more attributes
        }

        return pokemon_data
    else:
        # Print an error message if the request was not successful
        print(f"Failed to fetch Pokemon data. Status code: {response.status_code}")
        return None
    

def batch_fetch_pokemon_data(limit, offset=0):
    base_url = 'https://pokeapi.co/api/v2/pokemon/'
    
    # Set limit if higher than 24
    limit = min(limit, 24)

    # Send a GET request to the PokeAPI to get a list of Pokemon names
    response = requests.get(f'{base_url}?limit={limit}&offset={offset}')
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract Pokemon data from the results
        for pokemon in data['results']:
            pokemon_data = fetch_pokemon_details(pokemon['url'])
            
            # Append the data to the list
            if pokemon_data:
                pokemon_data_cache.append(pokemon_data)

        # return pokemon_data_cache  # Uncomment this line if you want to return the cache
    else:
        # Print an error message if the request was not successful
        print(f"Failed to fetch Pokemon names. Status code: {response.status_code}")
        return None


def fetch_pokemon_data_by_id(pokemon_id):
    # Check if data is already cached
    for pokemon_data in pokemon_data_cache:
        if pokemon_data['id'] == pokemon_id:
            return pokemon_data

    base_url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_id}'
    
    pokemon_data = fetch_pokemon_details(base_url)
    
    if pokemon_data['id'] == len(pokemon_data_cache) + 1:
        pokemon_data_cache.append(pokemon_data)
    
    return pokemon_data


def fetch_pokemon_data_by_name(pokemon_name):
    # Check if data is already cached
    for pokemon_data in pokemon_data_cache:
        if pokemon_data['name'] == pokemon_name:
            return pokemon_data

    base_url = f'https://pokeapi.co/api/v2/pokemon/{pokemon_name}'

    pokemon_data = fetch_pokemon_details(base_url)
    
    if pokemon_data['id'] == len(pokemon_data_cache) + 1:
        pokemon_data_cache.append(pokemon_data)
    
    return pokemon_data


# Pre-cache the first batch of 24 pokemons
batch_fetch_pokemon_data(5, 0)
#print(pokemon_data_cache)
#pokemon1 = fetch_pokemon_data_by_id(149)
#print(pokemon1)
#pokemon2 = fetch_pokemon_data_by_name("gyarados")
#print(pokemon2)

##################################################################################################
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# TODO: Error handling 
#@app.errorhandler(HTTPException)
#def page_not_found(e):
#    return render_template('404.html'), 404


##################################################################################################
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/login", methods = ["GET", "POST"])
def login():
    """Log user in"""
    
    # Forget any user_id
    session.clear()
    
    # User reached route via POST
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Input validation
        if not username:
            flash("Username is empty", "error")
            return render_template("homepage.html")
        
        elif not password:
            flash("Password is empty", "error")
            return render_template("homepage.html")
        
        # Query database for user
        existing_user = Users.query.filter_by(username=username).first()
        
        # Ensure username exists and password is correct
        if not existing_user:
            flash("User doesn't exist", "error")
            return render_template("homepage.html")
        
        if not check_password_hash(existing_user.password, password):
            flash("Incorrect password", "error")
            return render_template("homepage.html")
        
        # Remember which user has logged in
        session["user_id"] = existing_user.id
        
        # Redirect user to home page
        flash("User has logged in", "success")
        return redirect("/")
    
    # User reacher route via GET
    else:
        return render_template("homepage.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    
    return redirect("/")


@app.route("/register", methods = ["GET", "POST"])
def register():
    """Register a new user"""
    
    # User reached route via POST
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        # Input validation
        if not username:
            flash("Username is empty", "error")
            return render_template("register.html")
        
        elif not password:
            flash("Password is empty", "error")
            return render_template("register.html")
        
        elif not confirmation:
            flash("Password confirmation is empty", "error")
            return render_template("register.html")
        
        elif confirmation != password:
            flash("Passwords do not match", "error")
            return render_template("register.html")
        
        # Ensure username is available 
        existing_user = Users.query.filter_by(username=username).first()
        if existing_user:
            flash("Username is taken", "error")
            return render_template("register.html")
        
        # Ensure password has at least 8 characters
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template("register.html")
        
        # TODO: Ensure password has at least 2 digits and 1 uppercase letter
        #if not re.search(r'\d.*\d', password) or not any(char.isupper() for char in password):
        #    flash("Password must have at least 2 digits and 1 uppercase letter", "error")
        #    return render_template("register.html")
        
        # Insert user into database
        new_user = Users(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        # Log in the new user
        session["user_id"] = new_user.id
        
        # Redirect user to home page 
        flash("Registration successful", "success")
        return redirect("/")
    
    # User reacher route via GET
    else:
        return render_template("register.html")
##################################################################################################


@app.route("/about")
def about():
    # TODO:
    return render_template("about.html")


@app.route("/encyclopedia", methods = ["GET", "POST"])
@login_required
def encyclopedia():
    # TODO:
        
    return render_template("encyclopedia.html", pokemon_sprites_cache=pokemon_sprites_cache)


@app.route("/pokedex", methods = ["GET", "POST"])
@login_required
def pokedex():
    # TODO:
    
    # Initialize i in the session if it's not set
    if "i" not in session:
        session["i"] = 0
    
    # User reached route via POST
    if request.method == "POST":
        action = request.form["action"]
        number_pokemons = len(pokemon_data_cache)
        pokemon_name = request.form.get("pokemon_name")
        
        # If user clicks "Next"
        if action == "next":
            session["i"] += 1
            
            # If needs to cache a new pokemon
            if session["i"] == number_pokemons:
                pokemon_data = fetch_pokemon_data_by_id(number_pokemons + 1)
        
        # If user clicks "Previous"    
        elif action == "previous":
            if session["i"] > 0:
                session["i"] -= 1
                
        # If user searches for a pokemon
        elif action == "search":
            pokemon_data = fetch_pokemon_data_by_name(pokemon_name)
            i = pokemon_data['id'] - 1
            return render_template("pokedex-search.html", i=i, pokemon_sprites_cache=pokemon_sprites_cache, pokemon_data=pokemon_data)
        
    # User reached route via GET or went back to 1st pokemon
    i = session["i"]

    return render_template("pokedex.html", i=i, pokemon_sprites_cache=pokemon_sprites_cache, pokemon_data_cache=pokemon_data_cache)

        

@app.route("/party-selector", methods = ["GET", "POST"])
@login_required
def party_selector():
    # TODO:
    return render_template("party-selector.html")


@app.route("/settings", methods = ["GET", "POST"])
@login_required
def settings():
    # TODO:
    return render_template("settings.html")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables before running the app
    app.run(debug=True)