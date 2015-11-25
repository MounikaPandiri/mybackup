import pdf
from validator import *
from table import *
from pie import *
from barchart import *
from graph import *
from ptext import *

class PDFInstance(object):
    def __init__(self):
        self.obj_list = []
        self.table_data = {}
        self.serial_id = 0
        super(PDFInstance, self).__init__()


    def graph(self, result):
        graph_data = result['report']['graph']['graph_data']
        response = validate_chart_data(graph_data)
        if response[0] == 'FAIL':
            print "Malformed Graph Data : : " + response[1]
        self.obj_list.append(create_graph(graph_data))
   

    def barChart(self, result):
        bar_data = result['report']['barChart']['bar_data']
        response = validate_chart_data(bar_data)
        if response[0] == 'FAIL':
            print "Malformed BarChart Data : : " + response[1]
        self.obj_list.append(create_barchart(bar_data))
  

    def table(self,result):
        table_data = result['report']['table']['table_data']
        response = validate_table_data(table_data)
        if response[0] == 'FAIL':
            print "Malformed Table Data : : " + response[1]
        self.obj_list.append(create_table(table_data))
 
 
    def table_append(self,result):
        self.serial_id = self.serial_id + 1
        table_data = result['report']['table_append']['table_data']
        table_data['header'].append('Serial #')
        table_data['data'][0].append(self.serial_id)
        if self.serial_id == 1:
            self.table_data = table_data
        else:
            self.table_data['data'].append(table_data['data'][0])


    def pie(self,result):
        pie_data = result['report']['pie']['pie_data']
        response = validate_pie_data(pie_data)
        if response[0] == 'FAIL':
            print "Malformed Pie Data : : " + response[1]
        self.obj_list.append(create_pie(pie_data))


    def ptext(self,result):
        ptext_data = result['report']['ptext']['ptext_data']
        self.obj_list.append(create_ptext(ptext_data,9))


    def create_pdf(self, title_string, report_dir, result_dir):
        if self.serial_id > 0:
           self.table({'report':{'table':{'table_data': self.table_data}}})
        pdf.genpdf(self.obj_list, title_string, report_dir, result_dir)
