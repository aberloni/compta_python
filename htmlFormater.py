# https://blog.aspose.com/pdf/create-pdf-files-in-python/

# import pdfkit

# pdfkit.from_file()

def wrapAssoc(id, label, value, wrapClass = ""):
    
    output = "<div id=\""+id+"\""

    if len(wrapClass) > 0:
       output += "class=\""+wrapClass+"\""
    
    output += ">"
    
    output += "<span id=\""+id+"-label\">"+label+"</span>"
    output += "<span id=\""+id+"-value\">"+str(value)+"</span>"
    output += "</div>"

    return output


def wrapSection(section, content):
    output = "<"+section+">"

    output += content

    output += "</"+section+">"

    return output

def generateHeader(project):
    
    import generate

    if project == None:
        print("no project ?")
        return

    output = "<div id=\"header\">"

    autoe = generate.Assoc("autoe")

    # header : name & job
    output += "<div id=\"job\">"
    output += "<span id=\"job-personal-name\" class=\"vCenter\">"+autoe.filterKey("name")+"</span>"
    output += "<span id=\"job-name\" class=\"vCenter\">"+autoe.filterKey("job")+"</span>"
    output += "</div>"

    # header : infos
    output += "<div id=\"infos\">"

    output += "<div id=\"infos-impots\" class=\"float\">"
    output += "<div class=\"bold\">SIREN "+autoe.filterKey("siren")+"</div>"
    output += "<div class=\"bold\">URSSAF"+autoe.filterKey("siren")+"</div>"
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
    
    output += "<hr/>"

    output += "</div>" # /header

    return output

def generateBill(project, bill):

    output = "<div id=\"bill\">"
    
    import generate
    assoc = generate.Assoc("statics")

    output += "<div id=\"dispense\">"+assoc.filterKey("dispense")+"</div>"

    output += wrapAssoc("bill-header", "FACTURE", bill.id)

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

    cnt = bill.countDays()
    price = cnt * int(project.assoc.filterKey("taux"))

    output += "<div id=\"tasks-lines\">"
    output += "<span class=\"task-date\">"+bill.getLabelDate()+"</span>"
    output += "<span class=\"task-designation\">Developpement de fonctionnlitées : "+str(cnt)+" j</span>"
    output += "<span class=\"task-price\">"+str(price)+"€ HT</span>"
    output += "</div>"


    output += "</div>"

    output += "</div>" # /bill

    return output

def generateRib():
    output = ""

    import generate;

    rib = generate.Assoc("rib")

    output += "<hr/>"
    output += "<div id=\"rib\">"
    
    output += wrapAssoc("titulaire", "Titulaire", rib.filterKey("titulaire"))
    output += wrapAssoc("domicile", "Domiciliation", rib.filterKey("domicile"))
    output += wrapAssoc("refs", "References bancaires", rib.filterKey("refs"))
    output += wrapAssoc("iban", "IBAN", rib.filterKey("iban"))
    output += wrapAssoc("bic", "BIC SWIFT", rib.filterKey("bic"))

    output += "</div>"

    return output

def generateContact():
    output = ""

    import generate
    autoe = generate.Assoc("autoe")

    output += "<div id=\"contact\">"
    
    output += wrapAssoc("email", "Email", autoe.filterKey("email"), "float")
    output += wrapAssoc("phone", "Mobile", autoe.filterKey("phone"), "float")
    output += "<div class=\"clear\"></div>"

    output += "</div>"

    return output



def generateHtml(fileName, project, billDateStr):

    print("---HTML GENERATOR---")
    
    if project == None:
        print("no project ?")
        return

    project.dump()

    bill = project.getBill(billDateStr)

    html = ""

    # HEAD 
    
    head = ""
    head += "<title>"+bill.id+"</title>"
    head += "<link rel=\"stylesheet\" type=\"text/css\" href=\"css.css\" />"
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

    import configs

    fn = fileName + ".html"
    f = open(configs.pathExport+fn, "w")
    f.write(html)
    f.close()

    print("generated : "+fn)