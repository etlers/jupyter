import multiprocessing
import time

def func(x):
    time.sleep(x)
    print(x + 2)
    
def execute():
    manager = multiprocessing.Manager()
    processes = []
    
    for x in range([1,5,3]):
        p = multiprocessing.Process(target=func, args=(i,))
        
        processes.append(p)
        p.start()

    for process in processes:
        start = time.time()
        process.join()
        print("(Time elapsed: {}s)".format(int(time.time() - start)))

if __name__ == "__main__":
    execute()