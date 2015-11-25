from report import *
from ptext import *
import ptext
import pdf


def test_pdf():
    graph_data = { "graph_data" : {
                    "label" : [("1","2","3","4","5")],
                    "data" : [(1,2,3,4,5)],
                    "legend" : [("1","2","3","4","5")]
                    }
                 }

    bar_data = { "bar_data" : {
                    "label" : [("1","2","3","4","5")],
                    "data" : [(1,2,3,4,5)],
                    "legend" : [("1","2","3","4","5")]
                    }
                }
    table_data = { "table_data" : {
                    "header" : ['Scenario','Test-Setup', 'Config Name','VCPUs','RAM', 'Call Rate','KPI'],
                    "data" : [['SINGLE_NODE','IMS', ['vHS','vBono','vEllis','vHomer','vSprout'],'1',4096, 24.6069,0],
                              ['SINGLE_NODE','Setup-1', [''],'3',1024, 25,1],
                              ['MULTI_NODE','Setup-2', ['vHS','vBono','vEllis','vHomer'],'2',2048, 26,2]
                             ]
                    }
                 }
    #usage_data = [['MULTI_NODE','Setup-2', ['vHS','vBono','vEllis','vHomer'],'2','2048', '26','2']]
    #usage_data = [['MULTI_NODE','Setup-2', ['vHS','vBono'],'2',2048, 26,2]]
    #usage_data = [['SINGLE_NODE','IMS', ['vHS','vBono','vEllis','vHomer','vSprout'],'1',4096, 24.6069,0],
    #              ['SINGLE_NODE','Setup-1', ['vHS'],'3',1024, 25,1],
    #              ['MULTI_NODE','Setup-2', ['vHS','vBono','vEllis','vHomer'],'2',2048, 26,2]
    #             ]
    #usage_data = [['SINGLE_NODE','IMS', ['vHS','vBono','vEllis','vHomer','vSprout'],'1',4096, 24.6069,0],
                #  ['SINGLE_NODE','Setup-1', '','3',1024, 25,1]
                # ]
    pie_data = { "pie_data" : {
                    "label" : ["1","2","3","4","5"],
                    "data" : [1,2,3,4,5],
                    "legend" : ["1","2","3","4","5"]
                    }
               }
    elements = []
    #elements.append(create_graph({}))    
    #elements.append(barChart(bar_data))    
    #elements.append(table(table_data))    
    #elements.append(pie(pie_data))    
    elements.append(create_ptext("hi hello","9"))
    pdf.genpdf(elements)
    pass


if __name__ == "__main__":
    test_pdf()
