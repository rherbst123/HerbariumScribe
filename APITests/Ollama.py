import requests

def generate_response(prompt):
    url = "http://localhost:11434"
    headers = {"Content-Type": "application/json"}
    data = {"model": "llama3.2-vision:11b", "prompt": prompt}

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['response']
    else:
        raise Exception("Request failed with status code:", response.status_code)

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    response = generate_response(prompt)
    print(response)