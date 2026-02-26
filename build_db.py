import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import pysrt
import chromadb
from chromadb.utils import embedding_functions

# 1. 设置数据路径
# BASE_DIR = "/mnt/d/sysu/10_myself/3_ani/ger sub/ordered"  # 你的根目录文件夹名
BASE_DIR = "d:/sysu/10_myself/3_ani/ger sub/ordered"  # 你的根目录文件夹名

# 2. 初始化本地向量数据库
# 数据会保存在当前目录下的 "german_subs_db" 文件夹中
client = chromadb.PersistentClient(path="./german_subs_db")

# 3. 使用开源的本地 Embedding 模型 (支持多语言)
# 第一次运行会自动下载模型 (约几百MB)，之后就是离线的
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2" 
)

# 创建或获取集合
collection = client.get_or_create_collection(
    name="german_learning",
    embedding_function=sentence_transformer_ef
)

def process_srt_files():
    ids = []
    documents = [] # 存放德语原文
    metadatas = [] # 存放元数据（剧名、集数、时间）

    id_counter = 0
    
    # 遍历目录结构
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".srt"):
                file_path = os.path.join(root, file)
                
                # 获取剧名 (文件夹名) 和 集数 (文件名)
                # 假设路径是 ORDERED/madoka/1.srt
                path_parts = os.path.normpath(file_path).split(os.sep)
                series_name = path_parts[-2] # madoka
                episode_name = os.path.splitext(file)[0] # 1
                
                try:
                    subs = pysrt.open(file_path, encoding='utf-8')
                except Exception as e:
                    print(f"读取失败 {file_path}: {e}")
                    continue

                print(f"正在处理: {series_name} - 第 {episode_name} 集...")

                for sub in subs:
                    text = sub.text.replace('\n', ' ').strip()
                    if not text: continue
                    
                    # 记录开始和结束时间
                    start_time = str(sub.start)
                    end_time = str(sub.end)

                    # 存入列表
                    documents.append(text)
                    metadatas.append({
                        "series": series_name,
                        "episode": episode_name,
                        "start": start_time,
                        "end": end_time
                    })
                    ids.append(str(id_counter))
                    id_counter += 1
                    
                    # 为了防止内存溢出，每100条存一次 (或者你可以一次性存)
                    if len(ids) >= 100:
                        collection.add(documents=documents, metadatas=metadatas, ids=ids)
                        ids, documents, metadatas = [], [], []

    # 存入剩余的数据
    if ids:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    print(f"处理完成！共存入 {collection.count()} 条字幕。")

if __name__ == "__main__":
    process_srt_files()
