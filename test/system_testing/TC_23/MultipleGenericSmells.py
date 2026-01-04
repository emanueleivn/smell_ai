import numpy as np
import pandas as pd



def matrix():
    # Matrici costanti
    matrix_a = [[1, 2], [3, 4]]
    matrix_b = [[5, 6], [7, 8]]

    # Uso scorretto di `np.dot`
    result = np.dot(matrix_a, matrix_b)  # Punto di rilevamento # noqa

def load_data(file_path):
    df = pd.read_csv(file_path)  # Manca esplicitazione di `dtype`
    return df
