
"""
doesn't really work
- needs another app installed
- lose formating because it's not open in browser
"""

# https://pypi.org/project/pdfkit/
# https://wkhtmltopdf.org/
# C:\Program Files\wkhtmltopdf\bin
# https://www.geeksforgeeks.org/python-convert-html-pdf/

"""
import pdfkit

path_wk = "C:/Program Files/wkhtmltopdf/bin/"
path_wk_exe = "wkhtmltopdf.exe"
path_wkhtmltopdf = path_wk + path_wk_exe
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# https://stackoverflow.com/questions/27673870/cant-create-pdf-using-python-pdfkit-error-no-wkhtmltopdf-executable-found
pdfkit.from_file(htmlFile, configs.pathExport+bill+".pdf", configuration=config)
#pdfkit.from_url("http://google.com", "out.pdf", configuration=config)
"""
