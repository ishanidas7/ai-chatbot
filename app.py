from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import openai
import pandas as pd
import os
import re
from dotenv import load_dotenv 



app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='.')
CORS(app)

def configure():
    load_dotenv()


# Load and clean data
df = pd.read_excel("products.xlsx")
df.columns = df.columns.str.strip()
df['Price'] = pd.to_numeric(df['Price'], errors='coerce')

def intelligent_search(user_message):
    """Completely rewritten intelligent search"""
    message = user_message.lower().strip()
    result = df[df["In Stock"] == "Yes"].copy()  # Start with only in-stock items
    
    print(f"\n🤖 INTELLIGENT SEARCH: '{user_message}'")
    print(f"📦 Starting with {len(result)} in-stock products")
    
    filters_applied = []
    
    # 1. GENDER DETECTION - STRICT
    if any(word in message for word in ["women", "woman", "female", "ladies", "girls"]):
        result = result[result["Gender"] == "Women"]
        filters_applied.append("Women's")
        print(f"👩 Women only: {len(result)} products")
    elif any(word in message for word in ["men", "man", "male", "boys", "guys"]) and "women" not in message:
        result = result[result["Gender"] == "Men"] 
        filters_applied.append("Men's")
        print(f"👨 Men only: {len(result)} products")
    
    # 2. CATEGORY DETECTION - Add shirt category
    categories_found = []
    if "kurti" in message:
        categories_found.append("Kurti")
    if any(word in message for word in ["shirt", "shirts"]):
        categories_found.extend(["T-Shirt"])  # Based on your data
    if "hoodie" in message:
        categories_found.append("Hoodie")
    if "top" in message and "laptop" not in message:
        categories_found.append("Top")
    if "jeans" in message:
        categories_found.append("Jeans")
    if "dress" in message:
        categories_found.append("Dress")
    if "blazer" in message:
        categories_found.append("Blazer")
    if "sweater" in message:
        categories_found.append("Sweater")
    if "shorts" in message:
        categories_found.append("Shorts")
    
    if categories_found:
        result = result[result["Category"].isin(categories_found)]
        filters_applied.append(f"Categories: {', '.join(categories_found)}")
        print(f"📂 Category filter {categories_found}: {len(result)} products")
    
    # 3. STYLE DETECTION
    styles_found = []
    if any(word in message for word in ["party", "partywear", "party wear"]):
        styles_found.append("Party Wear")
    if "formal" in message:
        styles_found.append("Formal")
    if "casual" in message:
        styles_found.append("Casual")
    if "ethnic" in message:
        styles_found.append("Ethnic")
    if any(word in message for word in ["sport", "sports", "gym"]):
        styles_found.append("Sportswear")
    if any(word in message for word in ["street", "streetwear"]):
        styles_found.append("Streetwear")
    
    if styles_found:
        result = result[result["Style"].isin(styles_found)]
        filters_applied.append(f"Styles: {', '.join(styles_found)}")
        print(f"🎨 Style filter {styles_found}: {len(result)} products")
    
    # 4. PRICE DETECTION
    max_price = None
    price_patterns = [r"under\s*₹?(\d+)", r"below\s*₹?(\d+)", r"less\s*than\s*₹?(\d+)", 
                     r"within\s*₹?(\d+)", r"budget\s*₹?(\d+)", r"₹(\d+)\s*or\s*less",
                     r"cheap", r"affordable"]
    
    for pattern in price_patterns:
        if pattern in ["cheap", "affordable"]:
            if pattern in message:
                max_price = 1000  # Define cheap as under 1000
                break
        else:
            match = re.search(pattern, message)
            if match:
                max_price = int(match.group(1))
                break
    
    if max_price:
        result = result[result["Price"] <= max_price]
        filters_applied.append(f"Under ₹{max_price}")
        print(f"💰 Price filter ≤₹{max_price}: {len(result)} products")
    
    # 5. COLOR DETECTION
    colors_found = []
    color_keywords = ["red", "blue", "green", "pink", "yellow", "black", "white", "grey", "gray", "orange", "golden", "beige"]
    for color in color_keywords:
        if color in message:
            colors_found.append(color)
    
    if colors_found and "colour" in df.columns:
        color_mask = result["colour"].str.contains('|'.join(colors_found), case=False, na=False)
        color_filtered = result[color_mask]
        if len(color_filtered) > 0:
            result = color_filtered
            filters_applied.append(f"Colors: {', '.join(colors_found)}")
            print(f"🌈 Color filter {colors_found}: {len(result)} products")
    
    # Sort by price (cheapest first)
    if len(result) > 0:
        result = result.sort_values("Price")
    
    print(f"✅ FINAL: {len(result)} products after filters: {filters_applied}")
    return result, filters_applied, message

def create_intelligent_response(user_message, filtered_products, filters_applied, original_message):
    """Create smart, contextual responses - KEEP IT SHORT"""
    
    # Format products for AI
    if len(filtered_products) > 0:
        # Only show top 2 products for brevity
        product_details = []
        for _, row in filtered_products.head(2).iterrows():
            product_details.append(f"{row['Product Name']} - ₹{row['Price']} ({row['Category']}, {row['colour']})")
        
        product_text = "\n".join(product_details)
        filters_text = ", ".join(filters_applied) if filters_applied else "general search"
        
        prompt = f"""User asked: "{user_message}"
Found these matches:
{product_text}

Write a SHORT response (max 30 words):
- Mention 1-2 specific products with prices
- Be friendly but brief
- Example: "Perfect! Try our Women Jeans 30 in orange for ₹883 and Women Hoodie 15 in yellow at ₹1669 😊"
"""
    
    else:
        # Handle no results - SHORT version
        suggestions = df[df["In Stock"] == "Yes"].copy()
        
        # Apply partial filters for suggestions
        if any(word in original_message for word in ["women", "woman", "ladies"]):
            suggestions = suggestions[suggestions["Gender"] == "Women"]
        elif any(word in original_message for word in ["men", "man"]):
            suggestions = suggestions[suggestions["Gender"] == "Men"]
        
        # Get 1 popular item only
        popular_item = suggestions.head(1)
        if not popular_item.empty:
            row = popular_item.iloc[0]
            suggestion = f"{row['Product Name']} - ₹{row['Price']}"
        else:
            suggestion = "other great options"
        
        prompt = f"""User searched: "{user_message}"
No exact matches found.

Alternative: {suggestion}

Write a SHORT response (max 25 words):
- Say we don't have that specific item
- Suggest the alternative
- Stay positive
- Example: "We don't have that right now, but check out [product name] for ₹[price]!"
"""
        
        # Use suggestions as products to display
        filtered_products = popular_item
    
    return prompt, filtered_products

def format_product_list(products_df):
    """Format products for display"""
    if products_df.empty:
        return []
    
    product_cards = []
    for _, row in products_df.iterrows():
        image_path = str(row.get("Image Path", "")).strip()
        if not image_path or image_path.lower() == 'nan':
            product_name = str(row["Product Name"]).lower().replace(" ", "-")
            image_path = f"/static/images/{product_name}.jpg"
        elif not image_path.startswith('/static/'):
            image_path = f"/static/images/{image_path}"
        
        product_cards.append({
            "name": row["Product Name"],
            "price": int(row["Price"]) if pd.notna(row["Price"]) else 0,
            "size": row.get("Size", "N/A"),
            "style": row.get("Style", "N/A"),
            "gender": row.get("Gender", "N/A"),
            "category": row.get("Category", "N/A"),
            "colour": row.get("colour", "N/A"),
            "image": image_path,
        })
    
    return product_cards

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/images/<filename>')
def serve_image(filename):
    return send_from_directory('static/images', filename)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message.strip():
        return jsonify({
            "reply": "Hi! What are you looking for today? 😊", 
            "products": []
        })
    
    # Handle simple greetings
    if any(greeting in user_message.lower() for greeting in ["hi", "hello", "hey", "how are you"]):
        return jsonify({
            "reply": "Hello! I can help you find clothes. Try 'women kurti' ! 😊", 
            "products": []
        })
    
    # Perform intelligent search
    filtered_products, filters_applied, processed_message = intelligent_search(user_message)
    
    # Create smart response
    prompt, final_products = create_intelligent_response(user_message, filtered_products, filters_applied, processed_message)
    product_list = format_product_list(final_products)
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a helpful shopping assistant. 

IMPORTANT RULES:
- Keep responses VERY SHORT (maximum 30 words)
- Only mention 1-2 products with prices
- Be friendly but brief
- Use simple language
- No long explanations
- No styling advice unless asked

Examples of good responses:
"Perfect! Try Women Jeans 30 in orange for ₹883 😊"
"Great choice! Women Hoodie 15 in yellow at ₹1669 - perfect for parties!"
"Sorry, no heels available. Check out Women Top 25 for ₹999 instead!"
"""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=50  # Reduced from 350 to 50 for shorter responses
        )
        
        reply = response['choices'][0]['message']['content'].strip()
        
        # Remove any unwanted formatting
        reply = reply.replace("**", "").replace("*", "")
        
    except Exception as e:
        print(f"OpenAI Error: {e}")
        # Short fallback responses
        if len(product_list) > 0:
            reply = f"Found great options! Check out {product_list[0]['name']} for ₹{product_list[0]['price']} 😊"
        else:
            reply = "Sorry, no matches found. Try 'women kurti' !"
    
    return jsonify({"reply": reply, "products": product_list})

if __name__ == "__main__":
    app.run(debug=True)