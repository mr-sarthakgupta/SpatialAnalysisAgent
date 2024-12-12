import ast
import asyncio
import io
import json
import sys
import re
import traceback
# import openai
from collections import deque
from io import StringIO
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

import nest_asyncio
from IPython.core.display_functions import clear_output
from langchain_openai import ChatOpenAI
from openai import OpenAI

import configparser

# import networkx as nx
import logging
import time

import os
import requests
import networkx as nx
import pandas as pd
import geopandas as gpd
from pyvis.network import Network
# import processing

# Get the directory of the current script
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Add the directory to sys.path
if current_script_dir not in sys.path:
    sys.path.append(current_script_dir)

def load_LLM():
    huggingface_token = os.getenv("HF_TOKEN", "")
    
    model = AutoModelForCausalLM.from_pretrained(
        "meta-llama/Llama-3.2-1B-Instruct",
        token=huggingface_token,
        torch_dtype=torch.float32,
        device_map="cpu"
    )
    tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Llama-3.2-1B-Instruct",
        token=huggingface_token
    )
    return model, tokenizer

model, tokenizer = load_LLM()


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(current_script_dir, 'config.ini')
    config.read(config_path)
    return config


def load_OpenAI_key():
    config = load_config()  # Re-read the configuration file
    OpenAI_key = config.get('API_Key', 'OpenAI_key')
    return OpenAI_key


def create_openai_client():
    OpenAI_key = load_OpenAI_key()
    return OpenAI(api_key=OpenAI_key)


# def workspace_directory(path):
#     path =

import SpatialAnalysisAgent_Constants as constants
import SpatialAnalysisAgent_Codebase as codebase


# def create_OperationIdentification_promt(task):
#     OperationIdentification_requirement_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(constants.OperationIdentification_requirements)])
#
#     prompt =    f"Your role: {constants.OperationIdentification_role} \n" + \
#                 f"Your mission: {constants.OperationIdentification_task_prefix}: " + f"{task}\n\n" + \
#                 f"Requirements: \n{OperationIdentification_requirement_str} \n\n" + \
#                 f"List of QGIS tools: {codebase.algorithm_names} \n" +\
#                 f'Your reply example: {constants.OperationIdentification_reply_example}'
#     return prompt

# Add this function to generate the task name using GPT-3.5
def generate_task_name_with_gpt(task_description):
    prompt = f"Given the following task description: '{task_description}',give the best task that represents this task.\n\n" + \
             f"Provide the task name in just one or two words. \n\n" + \
             f"Underscore '_' is the only alphanumeric symbols that is allowed in a task name. A task_name must not contain quotations or inverted commas example or space. \n"
    # messages=[
    #         {"role": "user", "content": prompt},
    response = get_LLM_reply(prompt=prompt)

    task_name = response
    print(f"Task name: {task_name}")
    return task_name


def create_OperationIdentification_promt(task, data_path):
    OperationIdentification_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.OperationIdentification_requirements)])
    data_path = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(data_path)])

    prompt = f"Your role: {constants.OperationIdentification_role} \n" + \
             f"Your mission: {constants.OperationIdentification_task_prefix}: " + f"{task}" + f"and based on the properties of the data provided. The details of the data are below: " + f"\n{data_path}\n" + \
             f"Requirements: \n{OperationIdentification_requirement_str} \n\n" + \
             f"Customized tools:\n{constants.tools_index}\n" + \
             f"Your reply examples, depending on the task. Example 1: {constants.OperationIdentification_reply_example_1}\n " + " OR " + f"Example 2: {constants.OperationIdentification_reply_example_2}\n" + " OR " + f"Example 3: {constants.OperationIdentification_reply_example_3}"
    return prompt


def create_ToolSelect_prompt(task, data_path):
    ToolSelect_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.ToolSelect_requirements)])
    data_path_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(data_path)])

    prompt = f"Your role: {constants.ToolSelect_role} \n" + \
             f"Your mission: {constants.ToolSelect_prefix}: " + f"{task}\n\n" + \
             f"Based on the provided data {data_path_str}\n" + \
             f"Requirements: \n{ToolSelect_requirement_str} \n\n" + \
             f"Customized tools:\n{constants.tools_index}\n" + \
             f"Example for your reply: {constants.ToolSelect_reply_example2}\n"

    return prompt


def create_operation_prompt(task, data_path, selected_tools, documentation_str, workspace_directory):
    operation_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_requirement)])
    data_path_str = '\n'.join([f"{idx + 1}. {line}" for idx, line in enumerate(data_path)])
    prompt = f"Your role: {constants.operation_role} \n" + \
             f"Your mission: {constants.operation_task_prefix}: " + f"{task}" + "Using the following data paths: " + f"{data_path_str}" + "\nAnd this output directory: " + f"{workspace_directory}\n\n" + \
             f"Using the following Selected tool(s): {selected_tools}\n" + \
             f"Documentation of the selected tools: \n{documentation_str}\n" + \
             f"requirements: \n{operation_requirement_str}\n" + \
             f"Set: " + f"{workspace_directory}" + " as the output directory for any operation"
    return prompt


def code_review_prompt(extracted_code, data_path, selected_tool_dict, workspace_directory, documentation_str):
    operation_code_review_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_code_review_requirement)])
    # print(f"Code passed to review: {extracted_code}")
    operation_code_review_prompt = f"Your role: {constants.operation_code_review_role} \n" + \
                                   f"Your mission: {constants.operation_code_review_task_prefix} \n\n" + \
                                   f"The code is: \n----------\n{extracted_code}\n----------\n\n" + \
                                   f"The properties of the data are given below:\n{data_path}\n" + \
                                   f"Using the following selected tool(s):{selected_tool_dict}\n " + \
                                   f"The code examples in the Documentation: \n{documentation_str} can be used as an example while reviewing the {extracted_code} \n\n" + \
                                   f"The requirements for the code is: \n{operation_code_review_requirement_str}\n\n" + \
                                   f"Output directory that should be used:{workspace_directory}"
    return operation_code_review_prompt


# def get_code_for_operation(task_description, data_path, selected_tool, selected_tool_ID, documentation_str, review =True):
def get_code_for_operation(task_description, data_path, selected_tool, selected_tool_ID, selected_tool_dict, documentation_str,
                           review=True):
    operation_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_requirement)])
    prompt = f"Your role: {constants.operation_role} \n" + \
             f"Your mission: {constants.operation_task_prefix}: " + f"{task_description}\n\n" + "Using the following data paths:" + f"{data_path}" + \
             f"Selected tool: {selected_tool}\n" + \
             f'{selected_tool_ID} Documentation: \n{documentation_str}' + \
             f'requirements: \n{operation_requirement_str}'

    response = get_LLM_reply(
        prompt=prompt,
        system_role=constants.operation_role,
    )
    #Print the response
    extracted_code = extract_code(response)

    # Debugging: Print the operation_code to ensure it was extracted correctly
    print(f"Extracted Operation Code: {extracted_code}")
    if review:
        operation_code = ask_LLM_to_review_operation_code(extracted_code, selected_tool_ID, selected_tool_dict, documentation_str)
        return operation_code
    else:
        return extracted_code


def ask_LLM_to_review_operation_code(extracted_code, selected_tool_ID, selected_tool_dict, documentation_str):
    operation_code_review_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_code_review_requirement)])
    print(f"Code passed to review: {extracted_code}")
    operation_code_review_prompt = f"Your role: {constants.operation_code_review_role} \n" + \
                                   f"Your task: {constants.operation_code_review_task_prefix} \n\n" + \
                                   f"The code is: \n----------\n{extracted_code}\n----------\n\n" + \
                                    f"The selected tool(s) is: {selected_tool_dict}\n"+\
                                   f'{selected_tool_ID} Documentation: \n{documentation_str} \n\n' + \
                                   f"The requirements for the code is: \n{operation_code_review_requirement_str}"

    print("LLM is reviewing the operation code... \n")
    print(operation_code_review_prompt)

    # print(f"review_prompt:\n{review_prompt}")
    response = get_LLM_reply(prompt=operation_code_review_prompt,
                             system_role=constants.operation_role,
                             verbose=False,
                             stream=False,
                             retry_cnt=5,
                             )
    # new_operation_code = extract_code(response)
    # reply_content = extract_content_from_LLM_reply(response)
    # if (reply_content == "PASS") or (new_operation_code == ""): #if no modification
    #     print("Code review passed, no revision. \n\n")
    #     new_operation_code = code
    # # operation_code = operation_code

    return extract_code(response)


def convert_chunks_to_str(chunks):
    LLM_reply_str = ""
    for c in chunks:
        # print(c)

        cleaned_str = c.content.replace("```json", "").replace("```", "")
        LLM_reply_str += cleaned_str
        # # Append content, remove backticks, and strip leading/trailing whitespace

    return LLM_reply_str


def extract_dictionary_from_response(response):
    dict_pattern = r"\{.*?\}"
    match = re.search(dict_pattern, response)
    if match:
        dict_string = match.group()  # Extract the dictionary-like string
        # try:
        #     # Safely evaluate the dictionary string to convert it to an actual dictionary
        #     result_dict = ast.literal_eval(dict_string)
        #     print(result_dict)
        # except (SyntaxError, ValueError) as e:
        #     print("Error parsing the dictionary:", e)
    else:
        print("No dictionary found in the response.")

    return dict_string


def convert_chunks_to_code_str(chunks):
    LLM_reply_str = ""
    for c in chunks:
        # Append content, remove backticks, and strip leading/trailing whitespace
        LLM_reply_str += c.content
    return LLM_reply_str


def fix_json_format(incorrect_json_str):
    # Fix common JSON issues such as missing double quotes around keys
    # Example: convert {selected tool: ["Clip","Scatterplot"]} to {"selected tool": ["Clip","Scatterplot"]}
    fixed_json_str = re.sub(r'(\w+):', r'"\1":', incorrect_json_str)
    return fixed_json_str


def parse_llm_reply(LLM_reply_str):
    try:
        # Try to load the string directly as JSON
        selection_operation = json.loads(LLM_reply_str)
    except json.JSONDecodeError:
        # If it fails, try to fix the JSON format and decode again
        corrected_reply = fix_json_format(LLM_reply_str)
        try:
            selection_operation = json.loads(corrected_reply)
        except json.JSONDecodeError as e:
            # If it still fails, return None or raise an error as per your needs
            print(f"Failed to parse LLM reply: {e}")
            selection_operation = None
    except TypeError as e:
        # Catch the case where input is not a string, bytes, or bytearray
        print(f"TypeError: {e} - Input must be a valid JSON string.")
        selection_operation = None
    return selection_operation



def get_LLM_reply(prompt="Provide Python code to read a CSV file from this URL and store the content in a variable. ",
                  system_role=r'You are a professional Geo-information scientist and developer.',
                  verbose=True,
                  temperature=1,
                  stream=True,
                  retry_cnt=3,
                  sleep_sec=10,
                  ):
   

    messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
        
    prompt = tokenizer.apply_chat_template(
    messages, 
        tokenize=False,  # We want a string, not tokenized input
        add_generation_prompt=True  # Adds a generation prompt at the end
    )

    # Tokenize the prompt
    inputs = tokenizer(prompt, return_tensors="pt")

    response = tokenizer.decode(model.generate(**inputs, max_new_tokens=500)[0], skip_special_tokens=True)

    return response


def extract_content_from_LLM_reply(response):
    stream = False
    if isinstance(response, list):
        stream = True

    content = ""
    if stream:
        for chunk in response:
            chunk_content = chunk.choices[0].delta.content

            if chunk_content is not None:
                # print(chunk_content, end='')
                content += chunk_content
                # print(content)
        # print()
    else:
        content = response.choices[0].message.content
        # print(content)

    return content



#Fetching the streamed response of LLM
async def fetch_chunks(model, prompt_str):
    chunks = []
    async for chunk in model.astream(prompt_str):
        chunks.append(chunk)
        # print(chunk.content, end="", flush=True)
    return chunks


nest_asyncio.apply()


def extract_selected_tools(chunks):
    """
    Extracts and combines selected tools from a list of chunk dictionaries.

    :param chunks: List of dictionaries, each containing a "Selected tools" key.
    :return: A string of combined selected tools separated by commas.
    """
    all_tools = []

    for chunk in chunks:
        # Ensure the key exists and its value is a list
        tools = chunk.get("Selected tools", [])
        if isinstance(tools, list):
            all_tools.extend(tools)
        else:
            print(f"Warning: 'Selected tools' is not a list in chunk: {chunk}")

    # Optional: Remove duplicates while preserving order
    seen = set()
    unique_tools = []
    for tool in all_tools:
        if tool not in seen:
            seen.add(tool)
            unique_tools.append(tool)

    # Combine the tools into a single string separated by commas
    combined_tools_str = ', '.join(unique_tools)

    return combined_tools_str


def extract_code(response, verbose=False):
    '''
    Extract python code from reply
    '''
    # if isinstance(response, list):  # use OpenAI stream mode.
    #     reply_content = ""
    #     for chunk in response:
    #         chunk_content = chunk["choices"][0].get("delta", {}).get("content")
    #
    #         if chunk_content is not None:
    #             print(chunk_content, end='')
    #             reply_content += chunk_content
    #             # print(content)
    # else:  # Not stream:
    #     reply_content = response["choices"][0]['message']["content"]

    python_code = ""
    reply_content = extract_content_from_LLM_reply(response)
    python_code_match = re.search(r"```(?:python)?(.*?)```", reply_content, re.DOTALL)
    if python_code_match:
        python_code = python_code_match.group(1).strip()

    if verbose:
        print(python_code)

    return python_code


def extract_code_from_str(LLM_reply_str, verbose=False):
    '''
    Extract python code from reply string, not 'response'.
    '''

    python_code = ""
    python_code_match = re.search(r"```(?:python)?(.*?)```", LLM_reply_str, re.DOTALL)
    if python_code_match:
        python_code = python_code_match.group(1).strip()

    if verbose:
        print(python_code)

    return python_code


def execute_complete_program(code: str, try_cnt: int, task: str, model_name: str, documentation_str: str, data_path,
                             workspace_directory,
                             review=True) -> (str, str):
    count = 0
    output_capture = io.StringIO()
    original_stdout = sys.stdout  # Save the original stdout

    while count < try_cnt:
        print(f"\n\n-------------- Running code (trial # {count + 1}/{try_cnt}) --------------\n\n")
        original_stdout.flush()  # Ensure the message is printed immediately
        try:
            count += 1
            # Redirect stdout to capture print output
            sys.stdout = output_capture

            compiled_code = compile(code, 'Complete program', 'exec')
            exec(compiled_code, globals())  # pass only globals()

            # Restore original stdout after execution
            sys.stdout = original_stdout

            # Ensure that generated_output is returned or printed
            print(f"\n\n--------------- Done ---------------\n\n")
            return code, output_capture.getvalue()

        except Exception as err:
            sys.stdout = original_stdout  # Restore original stdout in case of error
            if count == try_cnt:
                print(f"Failed to execute and debug the code within {try_cnt} times.")
                return code, output_capture.getvalue()

            debug_prompt = get_debug_prompt(exception=err, code=code, task=task, data_path= data_path, documentation_str=documentation_str)
            print("Sending error information to LLM for debugging...")
            response = get_LLM_reply(prompt=debug_prompt,
                                     system_role=constants.debug_role,
                                     verbose=True,
                                     stream=True,
                                     retry_cnt=5,
                                     )
            code = extract_code(response)
            if review:
                print("\n\n-------------- REVIEWING THE DEBUG CODE ---------------\n\n")
                code = review_operation_code(extracted_code=code, data_path=data_path,
                                             workspace_directory=workspace_directory,
                                             documentation_str=documentation_str)
    return code, output_capture.getvalue()


def review_operation_code(extracted_code, data_path, workspace_directory, documentation_str):
    OpenAI_key = load_OpenAI_key()
    model = ChatOpenAI(api_key=OpenAI_key, model='gpt-4o', temperature=1)

    operation_code_review_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.operation_code_review_requirement)])
    operation_code_review_prompt = f"Your role: {constants.operation_code_review_role} \n" + \
                                   f"Your mission: {constants.operation_code_review_task_prefix} \n\n" + \
                                   f"The extracted code is: \n----------\n{extracted_code}\n----------\n\n" + \
                                   f"The code examples in the Documentation: \n{documentation_str} can be used as an example while reviewing the extracted_code \n\n" + \
                                   f"The requirements for the code is: \n{operation_code_review_requirement_str}\n\n" + \
                                   f"Replace the data path in the code example with:{data_path}\n\n" + \
                                   f"Set {workspace_directory} as the output directory for any operation"

    code_review_prompt_str_chunks = asyncio.run(fetch_chunks(model, operation_code_review_prompt))
    clear_output(wait=True)
    review_str_LLM_reply_str = convert_chunks_to_code_str(chunks=code_review_prompt_str_chunks)
    # EXTRACTING REVIEW_CODE

    print("\n")
    print(f"\n -------------------------- FINAL REVIEWED CODE -------------------------- \n")
    print("```python")
    reviewed_code = extract_code_from_str(LLM_reply_str=review_str_LLM_reply_str, verbose=True)
    # print(reviewed_code)
    # print("```")
    return reviewed_code


# def execute_complete_program(code: str, try_cnt: int, task: str, model_name: str, documentation_str: str) -> str:
#     count = 0
#
#     while count < try_cnt:
#         print(f"\n\n-------------- Running code (trial # {count + 1}/{try_cnt}) --------------\n\n")
#         try:
#             count += 1
#
#
#             compiled_code = compile(code, 'Complete program', 'exec')
#             exec(compiled_code, globals())  # #pass only globals() not locals()
#             # !!!!    all variables in code will become global variables! May cause huge issues!     !!!!
#
#
#             # Ensure that generated_output is returned or printed
#             print(f"\n\n--------------- Done ---------------\n\n")
#             return code
#
#         # except SyntaxError as err:
#         #     error_class = err.__class__.__name__
#         #     detail = err.args[0]
#         #     line_number = err.lineno
#         #
#         except Exception as err:
#
#             # cl, exc, tb = sys.exc_info()
#
#             # print("An error occurred: ", traceback.extract_tb(tb))
#             #
#
#             if count == try_cnt:
#                 print(f"Failed to execute and debug the code within {try_cnt} times.")
#                 return code
#
#             # print("code in execute_complete_program():", code)
#             #
#             debug_prompt = get_debug_prompt(exception=err, code=code, task=task, documentation_str=documentation_str)
#             print("Sending error information to LLM for debugging...")
#             # print("Prompt:\n", debug_prompt)
#             response = get_LLM_reply(prompt=debug_prompt,
#                                      system_role=constants.debug_role,
#                                      model=model_name,
#                                      verbose=True,
#                                      stream=True,
#                                      retry_cnt=5,
#                                      )
#             code = extract_code(response)
#
#     return code
#
#
# def capture_print_output(code: str) -> str:
#     # Create a StringIO object to capture printed output
#     output_capture = io.StringIO()
#     original_stdout = sys.stdout  # Save the original stdout
#
#     try:
#         # Redirect stdout to capture print output
#         sys.stdout = output_capture
#
#         # Compile and execute the code
#         compiled_code = compile(code, 'Complete program', 'exec')
#         exec(compiled_code, globals())  # Pass only globals()
#
#         # Restore original stdout after execution
#         sys.stdout = original_stdout
#
#         # Return captured output
#         return output_capture.getvalue()
#
#     except Exception as err:
#         # Restore original stdout in case of error
#         sys.stdout = original_stdout
#         print(f"Error occurred during code execution: {err}")
#         return ""


def get_debug_prompt(exception, code, task, data_path, documentation_str):
    etype, exc, tb = sys.exc_info()
    exttb = traceback.extract_tb(tb)  # Do not quite understand this part.
    # https://stackoverflow.com/questions/39625465/how-do-i-retain-source-lines-in-tracebacks-when-running-dynamically-compiled-cod/39626362#39626362

    print("code in get_debug_prompt:", code)
    ## Fill the missing data:
    exttb2 = [(fn, lnnr, funcname,
               (code.splitlines()[lnnr - 1] if fn == 'Complete program'
                else line))
              for fn, lnnr, funcname, line in exttb]

    # Print:
    error_info_str = 'Traceback (most recent call last):\n'
    for line in traceback.format_list(exttb2[1:]):
        error_info_str += line
    for line in traceback.format_exception_only(etype, exc):
        error_info_str += line

    print(f"Error_info_str: \n{error_info_str}")

    # print(f"traceback.format_exc():\n{traceback.format_exc()}")

    debug_requirement_str = '\n'.join(
        [f"{idx + 1}. {line}" for idx, line in enumerate(constants.debug_requirement)])

    debug_prompt = f"Your role: {constants.debug_role} \n" + \
                   f"Your task: {constants.debug_task_prefix} \n\n" + \
                   f"The properties of the data are given below:\n{data_path}\n" + \
                   f"Requirement: \n {debug_requirement_str} \n\n" + \
                   f"Your reply examples: {constants.OperationIdentification_reply_example_1} + ' or ' + '{constants.OperationIdentification_reply_example_2}'. \n\n " + \
                   f"The given code is used for this task: {task} \n\n" + \
                   f"When you are correcting the codes, Check the task again to ensure that the correct parameters (such as attributes, data paths) are being used. \n\n" + \
                   f"The technical guidelines for the code: \n {documentation_str} \n\n" + \
                   f"The error information for the code is: \n{str(error_info_str)} \n\n" + \
                   f"The code is: \n{code}"

    return debug_prompt


def has_disconnected_components(directed_graph, verbose=True):
    # Get the weakly connected components
    weakly_connected = list(nx.weakly_connected_components(directed_graph))

    # Check if there is more than one weakly connected component
    if len(weakly_connected) > 1:
        if verbose:
            print("component count:", len(weakly_connected))
        return True
    else:
        return False


def generate_function_def(node_name, G):
    '''
    Return a dict, includes two lines: the function definition and return line.
    parameters: operation_node
    '''
    node_dict = G.nodes[node_name]
    node_type = node_dict['node_type']

    predecessors = G.predecessors(node_name)

    # print("predecessors:", list(predecessors))

    # create parameter list with default values
    para_default_str = ''  # for the parameters with the file path
    para_str = ''  # for the parameters without the file path
    for para_name in predecessors:
        # print("para_name:", para_name)
        para_node = G.nodes[para_name]
        # print(f"para_node: {para_node}")
        # print(para_node)
        data_path = para_node.get('data_path', '')  # if there is a path, the function need to read this file

        if data_path != "":
            para_default_str = para_default_str + f"{para_name}='{data_path}', "
        else:
            para_str = para_str + f"{para_name}={para_name}, "

    all_para_str = para_str + para_default_str

    function_def = f'{node_name}({all_para_str})'
    function_def = function_def.replace(', )', ')')  # remove the last ","

    # generate the return line
    successors = G.successors(node_name)
    return_str = 'return ' + ', '.join(list(successors))

    # print("function_def:", function_def)  # , f"node_type:{node_type}"
    # print("return_str:", return_str)  # , f"node_type:{node_type}"
    # print(function_def, predecessors, successors)
    return_dict = {"function_definition": function_def,
                   "return_line": return_str,
                   'description': node_dict['description'],
                   'node_name': node_name
                   }
    return return_dict


def bfs_traversal(graph, start_nodes):
    visited = set()
    queue = deque(start_nodes)

    order = []
    while queue:
        node = queue.popleft()
        # print(node)
        if node not in visited:
            order.append(node)
            visited.add(node)
            queue.extend(neighbor for neighbor in graph[node] if neighbor not in visited)
    return order


def generate_function_def_list(G):
    '''
    Return a list, each string is the function definition and return line
    '''
    # start with the data loading, following the data flow.
    nodes = []
    # Find nodes without predecessors
    nodes_without_predecessors = [node for node in G.nodes() if G.in_degree(node) == 0]
    # print(nodes_without_predecessors)
    # Traverse the graph using BFS starting from the nodes without predecessors
    traversal_order = bfs_traversal(G, nodes_without_predecessors)

    # print("traversal_order:", traversal_order)

    def_list = []
    data_node_list = []
    for node_name in traversal_order:
        node_type = G.nodes[node_name]['node_type']
        if node_type == 'operation':
            # print(node_name, node_type)
            # predecessors = G.predecessors('Load_shapefile')
            # successors = G.successors('Load_shapefile') 

            function_def_returns = generate_function_def(node_name, G)
            def_list.append(function_def_returns)

        if node_type == 'data':
            data_node_list.append(node_name)

    return def_list, data_node_list


def get_given_data_nodes(G):
    given_data_nodes = []
    for node_name in G.nodes():
        node = G.nodes[node_name]
        in_degrees = G.in_degree(node_name)
        if in_degrees == 0:
            given_data_nodes.append(node_name)
            # print(node_name,in_degrees,  node)
    return given_data_nodes


def get_data_loading_nodes(G):
    data_loading_nodes = set()

    given_data_nodes = get_given_data_nodes(G)
    for node_name in given_data_nodes:

        successors = G.successors(node_name)
        for node in successors:
            data_loading_nodes.add(node)
            # print(node_name,in_degrees,  node)
    data_loading_nodes = list(data_loading_nodes)
    return data_loading_nodes


def get_data_sample_text(file_path, file_type="csv", encoding="utf-8"):
    """
    file_type: ["csv", "shp", "txt"]
    return: a text string
    """
    if file_type == "csv":
        df = pd.read_csv(file_path)
        text = str(df.head(3))

    if file_type == "shp":
        gdf = gpd.read_file(file_path)
        text = str(gdf.head(2))  # .drop('geomtry')

    if file_type == "txt":
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
            text = ''.join(lines[:3])
    return text


def show_graph(G):
    if has_disconnected_components(directed_graph=G):
        print("Disconnected component, please re-generate the graph!")

    nt = Network(notebook=True,
                 cdn_resources="remote",
                 directed=True,
                 # bgcolor="#222222",
                 # font_color="white",
                 height="800px",
                 # width="100%",
                 #  select_menu=True,
                 # filter_menu=True,

                 )

    nt.from_nx(G)

    sinks = find_sink_node(G)
    sources = find_source_node(G)
    # print("sinks:", sinks)

    # Set node colors based on node type
    node_colors = []
    for node in nt.nodes:
        # Check if 'node_type' key exists
        if 'node_type' not in node:
            print(f"Warning: node {node['label']} does not have 'node_type'. Skipping this node.")
            continue
        # print('node:', node)
        if node['node_type'] == 'data':
            #print('node:', node)
            if node['label'] in sinks:
                node_colors.append('violet')  # lightgreen
                #print(node)
            elif node['label'] in sources:
                node_colors.append('lightgreen')  # 
                #print(node)
            else:
                node_colors.append('orange')

        elif node['node_type'] == 'operation':
            node_colors.append('deepskyblue')

            # Update node colorsb
    for i, color in enumerate(node_colors):
        nt.nodes[i]['color'] = color
        # nt.nodes[i]['shape'] = 'box'
        nt.nodes[i]['shape'] = 'dot'
        # nt.set_node_style(node, shape="box")

    return nt


def find_sink_node(G):
    """
    Find the sink node in a NetworkX directed graph.

    :param G: A NetworkX directed graph
    :return: The sink node, or None if not found
    """
    sinks = []
    for node in G.nodes():
        if G.out_degree(node) == 0 and G.in_degree(node) > 0:
            sinks.append(node)
    return sinks


# Function to find the source node
def find_source_node(graph):
    # Initialize an empty list to store potential source nodes
    source_nodes = []

    # Iterate over all nodes in the graph
    for node in graph.nodes():
        # Check if the node has no incoming edges
        if graph.in_degree(node) == 0:
            # Add the node to the list of source nodes
            source_nodes.append(node)

    # Return the source nodes
    return source_nodes
