from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3")
llm.invoke("The meaning of life is")