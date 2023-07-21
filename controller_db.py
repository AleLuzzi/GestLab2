import mysql.connector

conn = mysql.connector.connect(host="192.168.0.100",
                                   database="data",
                                   user="root",
                                   password='')

c = conn.cursor()


def _recupera_primi():
        c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Primi piatti'")
        return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]

def _recupera_secondi():
        c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Secondi piatti'")
        return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]
    
def _recupera_contorni():
    c.execute("SELECT prodotto, plu FROM prodotti WHERE merceologia ='Contorni'")
    return [{'prodotto': str(x[0]), 'plu': str(x[1])} for x in c]

def _recupera_progressivo_ingresso():
        c.execute("SELECT prog_acq FROM progressivi")
        prog_ingresso = c.fetchone()[0]
        return prog_ingresso

def _recupera_lista_fornitori():
        c.execute("SELECT azienda FROM fornitori WHERE flag1_ing_merce = 1")
        fornitori = []
        for lista in c:
            fornitori.extend(lista)
        return fornitori

def _lista_tagli(cat):
       lista = []
       lista.clear()
       c = conn.cursor()
       cat_merc = [cat,]
       query = 'SELECT taglio FROM tagli WHERE Id_Merceologia=%s'
       c.execute(query, cat_merc)
       for x in c:
               lista.extend(x)
       return lista
