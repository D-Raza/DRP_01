from django.shortcuts import render, redirect
from django.http import JsonResponse
from .RecipeParser import get_recipe_details
from .TescoSearch import searchTesco
from .AsdaSearch import searchAsda
from .SainsburysSearch import searchSainsburys
from .MorrisonsSearch import search_morrisons
from .NLP import cleanupIngredients
from .models import SavedRecipe, DietForm, DietaryRestriction, IngredientsForm, DeadClick
import concurrent.futures
import requests
import random
import json

dietary_preferences_key = 'dietary_preferences'
possible_preferences = [
    "vegan",
    "vegetarian",
    "gluten_free",
    "none",
]

def index(request):
    saved_preferences = False
    recommendation = "none"
    
    # User has submitted new dietary preferences (arriving from index's form submission)
    if request.method == 'POST':
        saved_preferences = True
        diet_form = DietForm(request.POST)
        if diet_form.is_valid():
            preferences = diet_form.cleaned_data
            request.session[dietary_preferences_key] = preferences
            for rec in possible_preferences:
                if preferences.get(rec):
                    recommendation = rec
                    break
    
    # User is visiting the homepage (arriving from elsewhere)
    elif request.method == 'GET':
        if dietary_preferences_key in request.session:
            # Existing session
            preferences = request.session[dietary_preferences_key]
            diet_form = DietForm(preferences)
            for rec in possible_preferences:
                if preferences.get(rec):
                    recommendation = rec
                    break
        else:
            # New session
            diet_form = DietForm()
        
    random_recipes = ["https://www.bbcgoodfood.com/recipes/vegan-jambalaya", "https://www.bbcgoodfood.com/recipes/asian-chicken-noodle-soup"
                      , "https://www.bbcgoodfood.com/recipes/easy-chicken-curry", "https://www.bbcgoodfood.com/recipes/chow-mein"]
    random_recipe = random_recipes[random.randint(0, len(random_recipes) - 1)]
    
    context = {
        'diet_form': diet_form,
        'recommendation': recommendation,
        'saved_preferences': saved_preferences,
        'random_recipe': random_recipe,
    }
    
    return render(request, "drpapp/index.html", context=context)

def recommendations(request):
    return render(request, "drpapp/recommendations.html")
def recommendations_vegan(request):
    return render(request, "drpapp/recommendations_ve.html")
def recommendations_vegetarian(request):
    return render(request, "drpapp/recommendations_v.html")
def recommendations_gluten_free(request):
    return render(request, "drpapp/recommendations_gf.html")

def links_missing(links):
    print(links.values())
    return any(link[0] == 'INVALID' for link in links.values())

def get_comp_price(total_price, links):
    if links_missing(links):
        print("missing   !!!!!!!!")
        return float(10000000) + float(total_price)
    else:
        return float(total_price)

def show_all_recipes(request):
    context = {
        'saved_recipes': SavedRecipe.objects.all()
    }
    return render(request, 'drpapp/all_saved_recipes.html', context=context)

def save_recipe(request):
    if request.method == 'POST':
        # recipe_url = request.POST.get('recipe_url')
        # ingredients = request.POST.get('ingredients')

        recipe_url = "www.google.com"
        ingredients = request.session.get('ingredients', [])
        print(ingredients)

        saved_recipe = SavedRecipe.objects.create(recipe_url=recipe_url, ingredients=ingredients)
        saved_recipe.save()
        saved_recipe_id = saved_recipe.id

        context = {
            'saved_recipe_id': saved_recipe_id,
            'saved_recipe': saved_recipe,
        }

        return render(request, 'drpapp/recipe_saved.html', context=context)
    else:
        return JsonResponse({'message': 'Invalid request'})


def comparison(request):
    original_ingredients_key = 'original_ingredients'
    full_ingredients_key = 'full_ingredients'
    ingredients_key = 'ingredients'
    new_ingredient_key = 'new_ingredient'
    original_ingredients = []
    full_ingredients = []
    ingredients = []

    # User updates the dietary preferences
    if request.method == 'POST':
        original_ingredients = request.session.get(original_ingredients_key, [])
        full_ingredients = request.session.get(full_ingredients_key, [])
        title = request.session.get('title', [])
        image = request.session.get('image', [])
        instrs = request.session.get('instrs', [])
        for key in request.POST.keys():
            if key != "csrfmiddlewaretoken":
                if key == new_ingredient_key:
                    new_ingredient = request.POST.get(new_ingredient_key)
                    if new_ingredient != "":
                        ingredients.append(new_ingredient)
                        full_ingredients.append(new_ingredient)
                        request.session[full_ingredients_key] = full_ingredients
                else:
                    ingredients.append(key)

        #STARTS HERE
        preferences = request.session.get('dietary_preferences')
        supermarket_functions = [
            total_price_sainsburys,
            total_price_asda,
            total_price_tesco,
            total_price_morrisons,
        ]
        num_threads = len(supermarket_functions)
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

        results = [executor.submit(fun, ingredients, preferences, request) for fun in supermarket_functions]
        concurrent.futures.wait(results)
        
        sainsburys_total_price, sainsburys_item_links = results[0].result()
        asda_total_price, asda_item_links = results[1].result()
        tesco_total_price, tesco_item_links = results[2].result()
        morrisons_total_price, morrisons_item_links = results[3].result() #tesco_total_price, tesco_item_links 
        executor.shutdown()

        cheapest_total_market = get_cheapest_market([
            get_comp_price(sainsburys_total_price, sainsburys_item_links),
            get_comp_price(asda_total_price, asda_item_links),
            get_comp_price(morrisons_total_price, morrisons_item_links),
            get_comp_price(tesco_total_price, tesco_item_links)
        ])

        # full_ingredients_sorted = []
        # for ingredient in full_ingredients:
        #     if any(link == 'INVALID' for link in [sainsburys_item_links[ingredient][0], 
        #                                         asda_item_links[ingredient][0],
        #                                         tesco_item_links[ingredient][0],
        #                                         morrisons_item_links[ingredient][0]]):
        #         full_ingredients_sorted.insert(0, ingredient)
        #     else:
        #         full_ingredients_sorted.append(ingredient)
        
        # ingredients_sorted = []
        # for ingredient in ingredients:
        #     if any(link == 'INVALID' for link in [sainsburys_item_links[ingredient][0], 
        #                                         asda_item_links[ingredient][0],
        #                                         tesco_item_links[ingredient][0],
        #                                         morrisons_item_links[ingredient][0]]):
        #         ingredients_sorted.insert(0, ingredient)
        #     else:
        #         ingredients_sorted.append(ingredient)

        # ingredients_form = IngredientsForm(full_ingredients=full_ingredients_sorted, ingredients=ingredients_sorted)
        # print(ingredients_form)

        show_table = True
        #ENDS HERE

    # User searches a recipe
    elif request.method == 'GET':
        query = request.GET.get('query', '')
        
        dietary_preferences = request.session.get('dietary_preferences')
        original_ingredients, title, image, instrs = get_recipe_details(query, dietary_preferences)
        title = title.title()
        full_ingredients = cleanupIngredients(original_ingredients)
        ingredients = full_ingredients
        request.session[original_ingredients_key] = original_ingredients
        request.session[full_ingredients_key] = full_ingredients
        request.session['title'] = title
        request.session['image'] = image
        request.session['instrs'] = instrs

        # STARTS HERE
        sainsburys_total_price, sainsburys_item_links = 0, []
        asda_total_price, asda_item_links = 0, []
        tesco_total_price, tesco_item_links = 0, []
        morrisons_total_price, morrisons_item_links = 0, [] #tesco_total_price, tesco_item_links 
        cheapest_total_market = "Sainsbury's"
        # ENDS HERE

        show_table = False
    
    ingredients = list(filter(None, list(map(lambda s: s.strip().title(), ingredients))))
    full_ingredients = list(filter(None, list(map(lambda s: s.strip().title(), full_ingredients)))) 
    ingredients_form = IngredientsForm(full_ingredients=full_ingredients, ingredients=ingredients)


    context = {
        original_ingredients_key : original_ingredients,
        full_ingredients_key     : full_ingredients,
        'ingredients'            : ingredients,
        'sainsburys_total_price' : sainsburys_total_price,
        'asda_total_price'       : asda_total_price,
        'tesco_total_price'      : tesco_total_price,
        'morrisons_total_price'  : morrisons_total_price,
        'sainsburys_item_links'  : sainsburys_item_links,
        'asda_item_links'        : asda_item_links,
        'tesco_item_links'       : tesco_item_links,
        'morrisons_item_links'   : morrisons_item_links,
        'ingredients_form'       : ingredients_form,
        'recipe_title'           : title,
        'recipe_image'           : image,
        'method'                 : instrs,
        'cheapest_total_market'  : cheapest_total_market,
        'show_table': show_table,
    }
    
    return render(request, "drpapp/comparison.html", context=context)

def diet(request):
    print("diet called")
    if request.method == 'POST':
        form = DietForm(request.POST)
        if form.is_valid():
            # save form data to the database
            print("Form valid:", form)
            instance = form.save()
            request.session['instance_id'] = instance.id
            # redirect to home page (index)
            return redirect('index')

    else:
        instance_id = request.session.get('instance_id')
        instance = DietaryRestriction.objects.filter(id=instance_id).first()
        form = DietForm(instance=instance)

    context = {'form': form }

    return render(request, 'drpapp/diet.html', context)

# For logging dead clicks
def log_dead_click(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Get request data info
        timestamp = data.get('timestamp')
        url = data.get('url')
        x = data.get('x') # x coordinate of click 
        y = data.get('y') # y coordinate of click
        tag_name = data.get('tag_name') 
        class_name = data.get('class_name')
        element_id = data.get('element_id')
        
        # Save the dead click to the database
        DeadClick.objects.create(
            timestamp=timestamp,
            url = url,
            x = x,
            y = y,
            tag_name = tag_name,
            class_name = class_name,
            element_id = element_id
        )       
        
        # Return a success message 
        return JsonResponse({'message': 'Dead click logged successfully!'})

# For viewing all dead clicks
def dead_clicks_list(request):
    # Get all dead clicks from the database
    dead_clicks = DeadClick.objects.all()
    
    context = {'dead_clicks': dead_clicks}
    
    return render(request, 'drpapp/dead_clicks_list.html', context)

def proxy_tesco_basket(request):
    print("proxy_tesco_basket called")
    if request.method == 'PUT':
        url = 'https://www.tesco.com/groceries/en-GB/trolley/items?_method=PUT'
        payload = request.body
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-GB,en;q=0.9',
            'path': '/groceries/en-GB/trolley/items?_method=PUT',
            'content-type': 'application/json',
            'referer': 'https://www.tesco.com/groceries/en-GB/trolley',
            'origin': 'https://www.tesco.com',
        }
        headers.update(request.headers)  # Include any other headers from the original request (CSRF)
        print("Headers from proxy to Tesco:")
        print(headers)
        response = requests.put(url, data=payload, headers=headers)
        
        # Pass the response from Tesco back to the client-side JavaScript
        print("Response from Tesco:", response.json())
        return JsonResponse(response.json())
    else:
        # Handle other HTTP methods if needed
        print("Invalid request method to proxy")
        return JsonResponse({'error': 'Invalid request method'})



def get_tesco_product_links(items):
    # A Tesco link looks like this: https://www.tesco.com/groceries/en-GB/products/<product-id>
    base_url = "https://www.tesco.com/groceries/en-GB/products/"
    for ingredient in items:
        if items[ingredient][0] != "INVALID":
            items[ingredient] = base_url + items[ingredient][0], items[ingredient][1]
    return items

def get_morrisons_product_links(items):
    # A Morrisons link looks like this: https://groceries.morrisons.com/products/<id>
    base_url = "https://groceries.morrisons.com/products/"
    for ingredient in items:
        if items[ingredient][0] != "INVALID":
            items[ingredient] = base_url + items[ingredient][0], items[ingredient][1]
    return items

def get_sainsburys_product_links(items):
    return items

def get_asda_product_links(items):
    # An ASDA link looks like this: https://groceries.asda.com/product/<product-id>
    base_url = "https://groceries.asda.com/product/"
    for ingredient in items:
        if items[ingredient][0] != "INVALID":
            items[ingredient] = base_url + items[ingredient][0], items[ingredient][1]
    return items
   
def money_value(price):
    if str(price)[0].isnumeric():
        val = price
    else:
        # remove the £ sign
        val = price[1:]
    return round(float(val), 2)

def tesco_worker(ingredient, items, preferences, request):
    ingredient_key = "-".join([ingredient, 't'] + ([] if preferences is None else list(filter(lambda k: preferences[k], preferences.keys()))))
    print(ingredient_key)
    if request.session.get(ingredient_key) is None:
        most_relevant_item = searchTesco(ingredient, preferences)
        if most_relevant_item is not None:
            price = most_relevant_item['price']
            price = money_value(price)
            item_id = most_relevant_item['id']
            items[ingredient] = item_id, '£' + f'{price:.2f}'
            request.session[ingredient_key] = item_id, price 
            return price
        else:
            items[ingredient] = "INVALID", "0"
            request.session[ingredient_key] = "INVALID", "0" 
            return 0
    else:
        item_id, price = request.session.get(ingredient_key)
        if item_id == "INVALID":
            items[ingredient] = "INVALID", "0"
            return 0
        items[ingredient] = item_id, '£' + f'{price:.2f}'
        return price
        
def sainsburys_worker(ingredient, items, preferences, request):
    ingredient_key = "-".join([ingredient, 's'] + ([] if preferences is None else list(filter(lambda k: preferences[k], preferences.keys()))))
    print(ingredient_key)
    if request.session.get(ingredient_key) is None:
        most_relevant_item = searchSainsburys(ingredient, preferences)
        if most_relevant_item is not None:
            price = most_relevant_item['retail_price']['price']
            price = money_value(price)
            items[ingredient] = most_relevant_item['full_url'], '£' + f'{price:.2f}'
            request.session[ingredient_key] = most_relevant_item['full_url'], price 
            return price
        else:
            items[ingredient] = "INVALID", "0"
            request.session[ingredient_key] = "INVALID", "0" 
            return 0
    else:
        full_url, price = request.session.get(ingredient_key)
        if full_url == "INVALID":
            items[ingredient] = "INVALID", "0"
            return 0
        items[ingredient] = full_url, '£' + f'{price:.2f}'
        return price

def asda_worker(ingredient, items, preferences, request):
    ingredient_key = "-".join([ingredient, 'a'] + ([] if preferences is None else list(filter(lambda k: preferences[k], preferences.keys()))))
    print(ingredient_key)
    if request.session.get(ingredient_key) is None:
        most_relevant_item = searchAsda(ingredient, preferences)
        if most_relevant_item is not None:
            # price is a string of the form £<price> (not a string for the tesco api though)
            price_str = most_relevant_item.get('price')
            price = money_value(price_str)
            item_id = most_relevant_item['id']
            items[ingredient] = item_id, '£' + f'{price:.2f}'
            request.session[ingredient_key] = item_id, price 
            return price
        else:
            items[ingredient] = "INVALID", "0"
            request.session[ingredient_key] = "INVALID", "0" 
            return 0 
    else: 
        item_id, price = request.session.get(ingredient_key)
        if item_id == "INVALID":
            items[ingredient] = "INVALID", "0"
            return 0
        items[ingredient] = item_id, '£' + f'{price:.2f}'
        return price


def morrisons_worker(ingredient, items, preferences, request):
    ingredient_key = "-".join([ingredient, 'm'] + ([] if preferences is None else list(filter(lambda k: preferences[k], preferences.keys()))))
    print(ingredient_key)
    if request.session.get(ingredient_key) is None:
        most_relevant_item = search_morrisons(ingredient, preferences)
        if most_relevant_item is not None:
            price = most_relevant_item['product']['price']['current']
            item_id = most_relevant_item['sku']
            items[ingredient] = item_id, '£' + f'{price:.2f}'
            request.session[ingredient_key] = item_id, price 
            return price
        else:
            items[ingredient] = "INVALID", "0"
            request.session[ingredient_key] = "INVALID", "0" 
            return 0
    else: 
        item_id, price = request.session.get(ingredient_key)
        if item_id == "INVALID":
            items[ingredient] = "INVALID", "0"
            return 0
        items[ingredient] = item_id, '£' + f'{price:.2f}'
        return price


def total_price_tesco(ingredients, preferences, request):
    items = {}
    num_threads = 2
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

    results = [executor.submit(tesco_worker, ingredient, items, preferences, request) for ingredient in ingredients]

    concurrent.futures.wait(results)

    total_price = 0
    for result in results:
        total_price += result.result()
    
    total_price = "{:.2f}".format(money_value(total_price))
    
    executor.shutdown()
    item_links = get_tesco_product_links(items)

    return total_price, item_links

def total_price_asda(ingredients, preferences, request):
    items = {}
    num_threads = 10
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

    results = [executor.submit(asda_worker, ingredient, items, preferences, request) for ingredient in ingredients]

    concurrent.futures.wait(results)

    total_price = 0
    for result in results:
        total_price += result.result()
    
    total_price = "{:.2f}".format(money_value(total_price))
    
    item_links = get_asda_product_links(items)

    executor.shutdown()

    return total_price, item_links

def total_price_sainsburys(ingredients, preferences, request):
    items = {}
    num_threads = 10
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)

    results = [executor.submit(sainsburys_worker, ingredient, items, preferences, request) for ingredient in ingredients]

    concurrent.futures.wait(results)

    total_price = 0
    for result in results:
        total_price += result.result()
    
    total_price = "{:.2f}".format(money_value(total_price))
    
    item_links = get_sainsburys_product_links(items)

    executor.shutdown()

    return total_price, item_links

def total_price_morrisons(ingredients, preferences, request):
    items = {}
    num_threads = 3
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)
    
    results = [executor.submit(morrisons_worker, ingredient, items, preferences, request) for ingredient in ingredients]
    
    concurrent.futures.wait(results)
    
    total_price = 0
    for result in results:
        total_price += result.result()
    
    total_price = "{:.2f}".format(money_value(total_price))
    
    item_links = get_morrisons_product_links(items)
    
    executor.shutdown()
    
    return total_price, item_links

def get_cheapest_market(prices):
    supermarket_names = ["Sainsbury's", "Asda", "Morrisons", "Tesco"] 
    return supermarket_names[prices.index(min(prices))]