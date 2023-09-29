# https://blog.aspose.com/pdf/create-pdf-files-in-python/

# import pdfkit

# pdfkit.from_file()

from datetime import datetime
import calendar

import configs

import database;

def wrapAssoc(id, label, value, wrapClass = ""):
    
    output = "<div id=\""+id+"\""

    if len(wrapClass) > 0:
       output += "class=\""+wrapClass+"\""
    
    output += ">"
    
    output += "<span id=\""+id+"-label\" class=\"assocLabel\">"+label+"</span>"
    output += "<span id=\""+id+"-value\" class=\"assocValue\">"+str(value)+"</span>"
    output += "</div>"

    return output


def wrapSection(section, content):
    output = "<"+section+">"

    output += content

    output += "</"+section+">"

    return output

def generateHeader(project):
    
    if project == None:
        print("no project ?")
        return

    output = "<div id=\"header\">"

    autoe = database.Assoc("autoe")

    # header : name & job
    output += "<div id=\"job\">"
    output += "<span id=\"job-personal-name\" class=\"vCenter\">"+autoe.filterKey("name")+"</span>"
    output += "<span id=\"job-name\" class=\"vCenter\">"+autoe.filterKey("job")+"</span>"
    output += "</div>"

    # header : infos
    output += "<div id=\"infos\">"

    output += "<div id=\"infos-impots\" class=\"float\">"
    output += "<div class=\"bold\">SIREN  "+autoe.filterKey("siren")+"</div>"
    output += "<div class=\"bold\">URSSAF "+autoe.filterKey("urssaf")+"</div>"
    output += "</div>"
    
    output += "<div id=\"infos-adresse-wrapper\" class=\"float\">"
    output += "<div id=\"infos-adresse\" class=\"bold\">Adresse</div>"
    output += "<div>"+autoe.filterHtmlValue("address")+"</div>"
    output += "</div>"

    output += "<div class=\"clear\"></div>"
    output += "</div>"

    # header : client

    client = project.client

    output += "<div id=\"client\">"
    output += "<div id=\"client-title\">CLIENT</div>"
    output += "<div id=\"client-name\">"+client.name+"</div>"
    output += "<div id=\"client-address\">"+client.assoc.filterHtmlValue("address")+"</div>"
    output += "</div>"
    
    output += "</div>" # /header

    return output

def generateBill(project, bill):

    output = "<div id=\"bill\">"
    
    assoc = database.Assoc("statics")

    output += "<div id=\"dispense\">"+assoc.filterKey("dispense")+"</div>"

    output += wrapAssoc("bill-header", "FACTURE", bill.getBillFullUid())

    output += "<div id=\"bill-object\">"
    output += "<span id=\"bill-object-label\">OBJET</span>"
    output += "<span id=\"bill-object-label-dec\">Developpement sur le projet :</span>"
    output += "<span id=\"bill-object-projectName\">"+project.name+"</span>"
    output += "</div>"

    output += "<div id=\"tasks\">"
    
    output += "<div id=\"tasks-header\">"
    output += "<span class=\"task-date\">Date</span>"
    output += "<span class=\"task-designation\">Designation</span>"
    output += "<span class=\"task-price\">Prix</span>"
    output += "</div>"

    months = bill.getTimespanMonths()
    
    if len(months) <= 0:
        exit("need month")
    
    #print("tasks months x", len(months))

    for m in months:
        
        # YYYY-M (no leading 0)
        #print("html:month:"+m)

        cnt = bill.countDays(m)
        ht = bill.getHT(m)

        dt = datetime.strptime(m, "%Y-%m")
        year = str(dt.year)
        month = str(dt.month)

        htmlMonth = calendar.month_abbr[int(month)]
        
        output += "<div id=\"tasks-lines\">"
        output += "<span class=\"task-date\">"+htmlMonth+" "+year+"</span>"
        output += "<span class=\"task-designation\">Developpement de fonctionnalitées : "+str(cnt)+" j</span>"
        output += "<span class=\"task-price\">"+str(ht)+"€ HT</span>"
        output += "</div>"
        
    output += "</div>" # /tasks

    cnt = bill.countDays()
    ht = bill.getHT()
    tva = bill.getTVA()
    perc = str(tva * 100)+"%"

    absTva = bill.getTvaTotal()
    ttc = bill.getTTC()

    output += "<div id=\"bill-total\">"
    output += wrapAssoc("taux", "taux", str(project.getTaux())+" € HT")
    output += wrapAssoc("totalHT", "Total HT", str(ht)+" € HT")
    output += wrapAssoc("tva","TVA ("+perc+")", str(absTva)+" €")
    output += wrapAssoc("total","Total à régler", str(ttc)+" € TTC")
    output += "</div>"

    output += "</div>" # /bill

    return output

def generateRib():
    output = ""

    rib = database.Assoc("rib")

    output += "<hr/>"
    output += "<div id=\"rib\">"
    
    output += wrapAssoc("titulaire", "Titulaire", rib.filterKey("titulaire"))
    output += wrapAssoc("domicile", "Domiciliation", rib.filterHtmlValue("domiciliation"))
    output += wrapAssoc("refs", "References bancaires", rib.filterKey("refs"))
    output += wrapAssoc("iban", "IBAN", rib.filterKey("iban"))
    output += wrapAssoc("bic", "BIC SWIFT", rib.filterKey("bic"))

    output += "</div>"

    return output

def generateContact():
    output = ""

    autoe = database.Assoc("autoe")

    output += "<div id=\"contact\">"
    
    output += wrapAssoc("email", "Email", autoe.filterKey("email"))
    output += wrapAssoc("phone", "Mobile", autoe.filterKey("phone"))
    
    output += "</div>"

    return output


def generateHtml(project, bill, exportFileName):

    print("---HTML GENERATOR---")
    
    if project == None:
        print("no project ?")
        return
    
    html = ""

    # HEAD 
    
    head = ""
    head += "<title>"+exportFileName+"</title>"
    head += "<link rel=\"stylesheet\" type=\"text/css\" href=\"../css.css\" />"
    # head += "<meta charset=\"UTF-8\" />"

    # ...
    html += wrapSection("head", head)

    # BODY
    body = "<div id=\"canvas\">"

    body += generateHeader(project)

    body += generateBill(project, bill)

    body += generateRib()
    body += generateContact()

    body += "</div>"

    html += wrapSection("body", body)

    # saving
    html = wrapSection("html", html)

    f = open(configs.pathExport + exportFileName + ".html", "w")
    f.write(html)
    f.close()

    print("generated HTML : "+exportFileName)