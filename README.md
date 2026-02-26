# Anime Deutsch Learning

## Preparation
1. Install Ollama
> If GPU is integrated graphics in Intel, look into https://github.com/intel/ipex-llm/blob/main/docs/mddocs/Quickstart/ollama_quickstart.zh-CN.md

2. ollama run qwen2.5:1.5b

## How to Run it
1. In the first time running the project, we need to build up the database by using the following command to run build_db.py. (Be careful for the sub Path inside it)
```
python build.py
```

2. Use the following command to start the Ollama
```
cd PATH\TO\ollama-ipex-llm-2.2.0-win
start-ollama.bat
```

3. Use following command to run app.py
```
streamlit run app.py
```
