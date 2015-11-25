from reportlab.platypus import *

def create_image():
    pass


def create_logo(path,width,height,align):
    im = Image(path,width,height)
    im.hAlign = align
    return im
