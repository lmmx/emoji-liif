import multiprocessing as mp
from multiprocessing import Process
from more_itertools import chunked
from tqdm import tqdm

__all__ = ["batch_multiprocess"]

def batch_multiprocess(function_list, n_cores=mp.cpu_count(), show_progress=True):
    """
    Run a list of functions on `n_cores` (default: all CPU cores),
    with the option to show a progress bar using tqdm (default: shown).
    """
    iterator = [*chunked(function_list, n_cores)]
    if show_progress:
        iterator = tqdm(iterator)
    for func_batch in iterator:
        procs = []
        for f in func_batch:
            procs.append(Process(target=f))
        for p in procs:
            p.start()
        for p in procs:
            p.join()

def sequential_process(function_list, n_cores=mp.cpu_count(), show_progress=False):
    """
    Dummy sequential version of `batch_multiprocess` to be swapped in
    when there's an error to debug in that
    """
    for func in function_list:
        func()
