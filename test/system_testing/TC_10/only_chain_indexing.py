import pandas as pd

def only_chain_indexing():
    # dtype esplicito → NON scatta il code smell "columns_and_datatype_not_explicitly_set"
    df = pd.DataFrame({'a': [1, 2, 3]}, dtype='int64')
    
    # chained indexing → code smell "Chain_Indexing"
    value = df['a'][0]
    return value
