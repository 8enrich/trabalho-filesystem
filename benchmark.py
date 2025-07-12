import timeit
import matplotlib.pyplot as plt
import numpy as np
import statistics # Usaremos para calcular a média

# Certifique-se de que as classes do sistema de arquivos estão em um arquivo 'filesystem.py'
from filesystem import FileSystem
from linkedfilesystem import LinkedFileSystem

def benchmark_escrita(fs_class, num_blocos_lista, tamanho_bloco, num_repeticoes):
    """
    Realiza o benchmark de escrita, executando várias vezes e retornando a média.
    """
    tempos_medios = []
    total_blocos_necessarios = sum(num_blocos_lista) * 2 + 50
    
    print(f"Iniciando benchmark de escrita para {fs_class.__name__}...")
    for num_blocos in num_blocos_lista:
        tempos_desta_execucao = []
        for i in range(num_repeticoes):
            fs = fs_class(num_blocks=total_blocos_necessarios, block_size=tamanho_bloco)
            conteudo = b'a' * (tamanho_bloco * num_blocos)
            
            stmt = lambda: fs.make_file([f"file_{num_blocos}", conteudo.decode()])
            
            # O número 1 aqui significa que timeit medirá o tempo de uma única execução da lambda,
            # já que o nosso loop de repetições já está controlando o número de amostras.
            tempo = timeit.timeit(stmt, number=1)
            tempos_desta_execucao.append(tempo)
        
        # Calcula a média das execuções para este número de blocos
        tempo_medio = statistics.mean(tempos_desta_execucao)
        tempos_medios.append(tempo_medio)
        print(f"  - {num_blocos} blocos: {tempo_medio:.6f}s")
        
    return tempos_medios

def benchmark_leitura(fs_class, num_blocos_lista, tamanho_bloco, num_repeticoes):
    """
    Realiza o benchmark de leitura, executando várias vezes e retornando a média.
    """
    tempos_medios = []
    total_blocos_necessarios = sum(num_blocos_lista) * 2 + 50
    
    print(f"Iniciando benchmark de leitura para {fs_class.__name__}...")
    for num_blocos in num_blocos_lista:
        tempos_desta_execucao = []
        for i in range(num_repeticoes):
            fs = fs_class(num_blocks=total_blocos_necessarios, block_size=tamanho_bloco)
            nome_arquivo = f"file_{num_blocos}"
            conteudo = b'a' * (tamanho_bloco * num_blocos)
            fs.make_file([nome_arquivo, conteudo.decode()])
            
            stmt = lambda: fs._cat([nome_arquivo])

            tempo = timeit.timeit(stmt, number=1)
            tempos_desta_execucao.append(tempo)

        tempo_medio = statistics.mean(tempos_desta_execucao)
        tempos_medios.append(tempo_medio)
        print(f"  - {num_blocos} blocos: {tempo_medio:.6f}s")
        
    return tempos_medios

def benchmark_movimentacao(fs_class, num_blocos_lista, tamanho_bloco, num_repeticoes):
    """
    Realiza o benchmark de movimentação, executando várias vezes e retornando a média.
    """
    tempos_medios = []
    total_blocos_necessarios = sum(num_blocos_lista) * 2 + 50

    print(f"Iniciando benchmark de movimentação para {fs_class.__name__}...")
    for num_blocos in num_blocos_lista:
        tempos_desta_execucao = []
        for i in range(num_repeticoes):
            fs = fs_class(num_blocks=total_blocos_necessarios, block_size=tamanho_bloco)
            nome_arquivo = f"file_{num_blocos}"
            conteudo = b'a' * (tamanho_bloco * num_blocos)
            
            fs.make_directory(["dir1"])
            fs.make_directory(["dir2"])
            fs.make_file([f"dir1/{nome_arquivo}", conteudo.decode()])

            stmt = lambda: fs.move([f"dir1/{nome_arquivo}", "dir2"])

            tempo = timeit.timeit(stmt, number=1)
            tempos_desta_execucao.append(tempo)

        tempo_medio = statistics.mean(tempos_desta_execucao)
        tempos_medios.append(tempo_medio)
        print(f"  - {num_blocos} blocos: {tempo_medio:.6f}s")
        
    return tempos_medios

if __name__ == "__main__":
    # --- Parâmetros do Benchmark ---
    tamanho_bloco = 512
    # Testa para arquivos que ocupam de 1 a 30 blocos, com passo 2
    num_blocos_teste = list(range(1, 31, 2)) 
    # Número de vezes que cada teste (para cada tamanho de bloco) será repetido para tirar a média
    NUM_REPETICOES = 10

    # --- Execução do Benchmark ---
    tempos_escrita_fs = benchmark_escrita(FileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)
    tempos_escrita_lfs = benchmark_escrita(LinkedFileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)

    tempos_leitura_fs = benchmark_leitura(FileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)
    tempos_leitura_lfs = benchmark_leitura(LinkedFileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)

    tempos_movimentacao_fs = benchmark_movimentacao(FileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)
    tempos_movimentacao_lfs = benchmark_movimentacao(LinkedFileSystem, num_blocos_teste, tamanho_bloco, NUM_REPETICOES)
    
    print("\nBenchmark concluído. Gerando gráficos...")

    # --- Geração dos Gráficos ---
    # Matplotlib é uma biblioteca popular para criar visualizações em Python.
    plt.style.use('seaborn-v0_8-whitegrid')

    # Gráfico de Desempenho de Escrita
    plt.figure(figsize=(12, 7))
    plt.plot(num_blocos_teste, tempos_escrita_fs, marker='o', linestyle='-', label='FileSystem (Contíguo)')
    plt.plot(num_blocos_teste, tempos_escrita_lfs, marker='x', linestyle='--', label='LinkedFileSystem (Encadeado)')
    plt.xlabel("Quantidade de Blocos")
    plt.ylabel(f"Tempo Médio de {NUM_REPETICOES} execuções (s)")
    plt.title("Benchmark de Desempenho de Escrita")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Gráfico de Desempenho de Leitura
    plt.figure(figsize=(12, 7))
    plt.plot(num_blocos_teste, tempos_leitura_fs, marker='o', linestyle='-', label='FileSystem (Contíguo)')
    plt.plot(num_blocos_teste, tempos_leitura_lfs, marker='x', linestyle='--', label='LinkedFileSystem (Encadeado)')
    plt.xlabel("Quantidade de Blocos")
    plt.ylabel(f"Tempo Médio de {NUM_REPETICOES} execuções (s)")
    plt.title("Benchmark de Desempenho de Leitura")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Gráfico de Desempenho de Movimentação
    plt.figure(figsize=(12, 7))
    plt.plot(num_blocos_teste, tempos_movimentacao_fs, marker='o', linestyle='-', label='FileSystem (Contíguo)')
    plt.plot(num_blocos_teste, tempos_movimentacao_lfs, marker='x', linestyle='--', label='LinkedFileSystem (Encadeado)')
    plt.xlabel("Quantidade de Blocos")
    plt.ylabel(f"Tempo Médio de {NUM_REPETICOES} execuções (s)")
    plt.title("Benchmark de Desempenho de Movimentação")
    plt.legend()
    plt.grid(True)
    plt.show()
