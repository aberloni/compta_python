app to generate billings

# generate bills

- declare client
- declare project
- declare bill, periode (start/end dates)
- solve html page of "days count X daily"
- print that html page

# regroup all statements of clients

- list clients
- gather all transactions in a daterange
- sort and display

# generate array of TVA declaration

- gather all billed data
- solve what is fully paid
- keep track of TVA declaration
- solve what was not declared yet /month

# deps

	pip install weasyprint
	pip install pdfplumber


this needs some other dependencies fetches by using pango

	https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation