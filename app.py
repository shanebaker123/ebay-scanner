import os
import requests
from bs4 import BeautifulSoup
import re
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

def get_product_title(barcode):
    # Try looking up as a book first
    if len(barcode) == 13 and barcode.startswith('978'):
        try:
            url = f"https://openlibrary.org:{barcode}&format=json&jscmd=data"
            res = requests.get(url, timeout=5).json()
            if f"ISBN:{barcode}" in res:
                return res[f"ISBN:{barcode}"]["title"]
        except Exception:
            pass
    
    # Try general merchandise lookup fallback
    try:
        upc_url = f"https://upcitemdb.com{barcode}"
        res = requests.get(upc_url, timeout=5).json()
        if "items" in res and len(res["items"]) > 0:
            return res["items"][0]["title"]
    except Exception:
        pass
        
    return None

def get_ebay_sold_average(search_title):
    try:
        formatted_title = search_title.replace(" ", "+")
        ebay_url = f"https://ebay.com{formatted_title}&_sacat=0&LH_Sold=1&LH_Complete=1"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(ebay_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_tags = soup.find_all('span', class_='s-item__price')
        prices = []
        
        for tag in price_tags:
            clean_text = tag.get_text().replace('$', '').replace(',', '')
            match = re.search(r'[\d.]+', clean_text)
            if match:
                prices.append(float(match.group()))
                
        if prices:
            # Skip first element layout template
            recent_prices = prices[1:11] if len(prices) > 1 else prices
            if recent_prices:
                return round(sum(recent_prices) / len(recent_prices), 2)
    except Exception:
        pass
    return 0.00

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/lookup')
def lookup():
    barcode = request.args.get('barcode', '')
    if not barcode:
        return jsonify({"error": "No barcode provided"}), 400
        
    title = get_product_title(barcode)
    if not title:
        return jsonify({"title": f"Unknown Item ({barcode})", "avg_sold": 0.00, "profit": 0.00})
        
    avg_sold = get_ebay_sold_average(title)
    
    # Simple Math: Estimated profit assuming you bought it for $2.00 
    # and subtracting a 15% rough eBay selling fee template standard
    estimated_fees = avg_sold * 0.15
    net_profit = round(avg_sold - estimated_fees - 2.00, 2)
    
    return jsonify({
        "title": title,
        "avg_sold": avg_sold,
        "profit": max(0.00, net_profit)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
