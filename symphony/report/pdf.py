from os.path import expanduser
from reportlab.lib.units import inch
from reportlab.lib import *
from reportlab.lib.pagesizes import *
from reportlab.platypus import *
from reportlab.lib.colors import Color, PCMYKColor
from ptext import *
from image import *
from table import *

def genpdf(data, title, report_dir, result_dir):
    home = expanduser("~")
    doc = SimpleDocTemplate(result_dir+'/test_results.pdf', pagesize=letter,rightMargin=72,leftMargin=72,topMargin=20,bottomMargin=18)
    elements = []
    usage_data = []


### add logo
    logo_path = report_dir+'/report/resources/tata2.jpg'
    elements.append(create_logo(logo_path,2*inch,1*inch,'CENTER'))


### define style for paragraph
    title_str = "<b>%s</b>"%title
    elements.append(create_ptext(title_str,16)) 
    elements.append(create_ptext("_________________________________________________________________________________",10))
    #elements.append(create_ptext("Summary",14))
    elements.append(Spacer(1, 18))


### Displaying Pdf elements
    for key in data:
        elements.append(key)
        if "_rowHeights" in dir(key):
            length=len(key._rowHeights)-1
            #if length is 1:
            #   elements.append(create_pctext("Displaying 1 Test Detail",7))
            #else:
            #   elements.append(Spacer(1, 28))
            #   ptext= "Displaying %s Test Details" %(length)
            #   elements.append(create_pctext(ptext,10))

            passed = 0
            fail = 0
            complete = 0
            for i in range(1,len(key._cellvalues)):
                if 'PASS' in (key._cellvalues)[i]:
                    passed = passed + 1
                else:
                    fail = fail + 1
            table_data = {
                    "header" : ['Test Scenario','Tests Passed', 'Tests Failed','Total Tests'],
                    "data" : [[key._cellvalues[1][0],passed,fail,length]
                             ]
                 }
            elements.append(create_pctext("Summary",14))
            elements.append(Spacer(1, 20))
            elements.append(create_table(table_data))

        elements.append(Spacer(1, 28))

    doc.build(elements)

