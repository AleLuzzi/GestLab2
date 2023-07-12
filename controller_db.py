import mysql.connector

conn = mysql.connector.connect(host="127.0.0.1",
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
