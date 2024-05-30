import os
import sys
import threading
import time
import json
import requests
import argparse
import subprocess

class Loading:
    def __init__(self):
        self.spinner = '|/-\\'
        self.spinner_index = 0
        self.running = False
        self.thread = None

    def hide_cursor(self):
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

    def show_cursor(self):
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

    def clear_line(self):
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()

    def update(self):
        while self.running:
            sys.stdout.write(f'\rWaiting for assistant response... {self.spinner[self.spinner_index]}')
            sys.stdout.flush()
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner)
            time.sleep(0.1)
        self.clear_line()
        self.show_cursor()

    def start(self):
        if not self.running:
            self.running = True
            self.hide_cursor()
            self.thread = threading.Thread(target=self.update)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()

def load_required_env_variables(var_name: str):
    value = os.getenv(var_name)
    if value is None:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            value = os.getenv(var_name)
            if value is None or value.strip() == "":
                print(f"Error: {var_name} environment variable is not defined. Please define it in a .env file or directly in your environment.")
                exit(1)
        except ImportError:
            print("Error: dotenv package is not installed. Please install it with 'pip install python-dotenv' or define the environment variables directly.")
            exit(1)
        except Exception as e:
            print(f"Error loading {var_name}: {e}")
            exit(1)
    return value

def load_config(api_key=None):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        print(f"Error: {config_path} not found. Please create the config file with the necessary configuration.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {config_path}: {e}")
        exit(1)

    api_key = load_required_env_variables('AIR_TOAD_API_KEY')
    if not api_key or api_key.strip() == "":
        print("Error: API key is not defined. Please ensure it is set in the environment variable.")
        exit(1)

    config['api_key'] = api_key
    return config

class Client:
    def __init__(self, api_key=None):
        self.config = load_config(api_key=api_key)
        self.api_key = api_key if api_key else self.config.get('api_key')
        self.base_url = self.config.get('base_url')
        self.version = self.config.get('version')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def post(self, endpoint, data):
        loading = Loading()
        url = f"{self.base_url}/{self.version}/{endpoint}"
        try:
            loading.start()
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            response = response.json()
            if 'error' in response and 'message' in response['error']:
                return response['error']['message']
            return response['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return "HTTP error occurred."
        except Exception as e:
            print(f"An error occurred: {e}")
            return "An error occurred."
        finally:
            loading.stop()

class Text:
    def __init__(self):
        self.client = None
        self.context = []

    def run(self, api_key=None, prompt=None, system_prompt=None, stream=None, json=None, temperature=None, max_tokens=None, top_p=None, seed=None, stop=None, ciq=False):
        self.client = Client(api_key=api_key)
        self.model = self.client.config.get('model')
        self.max_tokens = max_tokens if max_tokens else 1024
        if not prompt:
            print("Error: Invalid input detected. Please enter a valid message.")
            exit(1)
        if ciq:
            prompt = f"#You are a helpful assistant. PEP8 to 2 tab indentation atomized function made Golfed Terse Terser Terseness style coding updating old with oneliners in terminal sed - -e's/update_from_regex_pattern/into_this_update/g' $(ls -dt * | head -1)''')\n\n{prompt}"
        if json:
            if stream:
                print("Error: JSON mode does not support streaming.")
                exit(1)
            if stop:
                print("Error: JSON mode does not support stop sequences.")
                exit(1)
            if "json" not in prompt:
                prompt = prompt + " | Respond in JSON. The JSON schema should include at minimum: {'response': 'string', 'status': 'string'}"
            response_format = {"type": "json_object"}
        else:
            response_format = None
        if system_prompt:
            message = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        else:
            message = [{"role": "user", "content": prompt}]
        self.context.append({"role": "user", "content": prompt})
        data = {
            "messages": self.context,
            "response_format": response_format,
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
            "seed": seed,
            "stop": stop
        }
        data = {k: v for k, v in data.items() if v is not None}
        endpoint = self.client.config.get('completions_endpoint')
        if stream:
            response = self.client.post(endpoint, data)
            assistant_response = response
        else:
            response = self.client.post(endpoint, data)
            assistant_response = response
        self.context.append({"role": "assistant", "content": assistant_response})
        return assistant_response

def ensure_bashrc_function():
    bashrc_path = os.path.expanduser("~/.bashrc")
    script_path = os.path.abspath(__file__)
    function_definition = f'''function q() {{
    echo "Running AI Toad Terminal Companion..."
    if [ "$1" == "c" ]; then
        python {script_path} --conversation
    elif [ "$1" == "ciq" ]; then
        python {script_path} --conversation --ciq
    elif [ "$1" == "c" ] && [ "$2" == "ciq" ]; then
        python {script_path} --conversation --ciq
    else
        last_command=$(history | tail -n 2 | head -n 1 | sed "s/^[ ]*[0-9]*[ ]*//")
        last_output=$(eval "$last_command" 2>&1)
        if [ "$1" == "ciq" ]; then
            python {script_path} "$last_command" "$last_output" --ciq
        else
            python {script_path} "$last_command" "$last_output"
        fi
    fi
}}'''
    if os.path.exists(bashrc_path):
        with open(bashrc_path, 'r') as file:
            bashrc_content = file.read()
        if function_definition not in bashrc_content:
            with open(bashrc_path, 'a') as file:
                file.write(f"\n{function_definition}\n")
            print(f"Added q function to {bashrc_path}")
    else:
        with open(bashrc_path, 'w') as file:
            file.write(f"{function_definition}\n")
        print(f"Created .bashrc and added q function")

    # Source the .bashrc file
    subprocess.run(["bash", "-c", "source ~/.bashrc"])

def main():
    ensure_bashrc_function()

    parser = argparse.ArgumentParser(description="AI Toad Terminal Companion")
    parser.add_argument('last_command', type=str, nargs='?', help='Last executed command')
    parser.add_argument('last_output', type=str, nargs='?', help='Output of the last executed command')
    parser.add_argument('--conversation', action='store_true', help='Enable conversation mode')
    parser.add_argument('--ciq', action='store_true', help='Enable coding improvement query preparation')
    args = parser.parse_args()

    text = Text()

    if args.conversation:
        print("Welcome to the ai toad auto code terminal companion. Type 'exit' to quit.")
        while True:
            prompt = input("You: ")
            if prompt.lower() == 'exit':
                print("Goodbye!")
                break
            response = text.run(api_key=None, prompt=prompt, ciq=args.ciq)
            print(f"Assistant: {response}")
        print("Thank you for using the AI toad auto code terminal companion. Have a great day!")
    elif args.last_command and args.last_output:
        prompt = f"Command: {args.last_command}\nOutput: {args.last_output}"
        response = text.run(api_key=None, prompt=prompt, ciq=args.ciq)
        print(f"Assistant: {response}")
    else:
        print("Invalid usage. Please provide the last command and output or use the --conversation flag.")

if __name__ == "__main__":
    main()
