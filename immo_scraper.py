import csv
from dotenv import load_dotenv

from immowelt import get_results

# Load the environment variables from the .env file
load_dotenv()

# Open a CSV file to write the results
with open('immo_listings.csv', 'w', newline='', encoding='utf-8') as csvfile:
    results = get_results()
    fieldnames = ['title', 'price', 'area', 'ratio', 'link']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop through the results and extract the relevant information
    for result in results:
        # Write the information to the CSV file
        writer.writerow({
            'title': result.title,
            'price': result.price,
            'area': result.area,
            'ratio': result.ratio,
            'link': result.link
        })
