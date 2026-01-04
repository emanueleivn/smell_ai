import pandas as pd
import numpy as np

def chain_index_example():
    # Creazione di un DataFrame di esempio
    df = pd.DataFrame([1, 2, 3, 4], [5, 6, 7, 8])

    col = 1
    x = 0

    # Accesso concatenato (chain indexing)
    df[col][x] = 9
    df.loc[x, col] = 9

def matrix():
    # Matrici costanti
    matrix_a = [[1, 2], [3, 4]]
    matrix_b = [[5, 6], [7, 8]]

    # Uso scorretto di `np.dot`
    result = np.dot(matrix_a, matrix_b)  # Punto di rilevamento # noqa
