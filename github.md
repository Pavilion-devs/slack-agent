RunnableParallel invoke function causes AttributeError: 'dict' object has no attribute 'replace' #17773
Unanswered
raghuldeva asked this question in Q&A
RunnableParallel invoke function causes AttributeError: 'dict' object has no attribute 'replace'
#17773
@raghuldeva
raghuldeva
on Feb 20, 2024 · 5 comments · 4 replies
Return to top

raghuldeva
on Feb 20, 2024
Checked other resources
 I added a very descriptive title to this question.
 I searched the LangChain documentation with the integrated search.
 I used the GitHub search to find a similar question and didn't find it.
Commit to Help
 I commit to help with one of those options 👆
Example Code
def load_llm():
    llm = VLLM(model="/zephyr-7B-beta-AWQ",quantization="awq",trust_remote_code=True,tensor_parallel_size=1,max_new_tokenxs=1024,batch_size = 3,top_k=50,top_p=0.9,temperature=0.1,repetition_penalty=1.1,st>
    return llm

llm = load_llm()

db = ElasticsearchStore(es_url="http://localhost:9200", index_name="test-basic", embedding=embeddings, strategy=ElasticsearchStore.ExactRetrievalStrategy())

retriever1 = db.as_retriever(search_kwargs={"k": 2,"score_threshold":0.8})
print("RETRIEVER IS : ", retriever1)

rag_prompt = hub.pull("rlm/rag-prompt")

chain = (
       {"context": retriever1, "question": RunnablePassthrough()}
       | rag_prompt
       | llm
       | StrOutputParser()
       )

query = "What is compliance?"

rag_chain_with_source = RunnableParallel(context=retriever1, question=RunnablePassthrough()).assign(answer=chain)

print("RAG chin with source : ", rag_chain_with_source.invoke(input_data))
Description
I'm trying to use Elasticsearchstore to retrieve, pass it to chain, and get answer from LLM along with source documents.

When I try to use RunnableParallel and invoke it, the error I see is

File "/EC_chainlit/inference.py", line 117, in
print("RAG chin with source : ", rag_chain_with_source.invoke(query))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2053, in invoke
input = step.invoke(
^^^^^^^^^^^^
File "lib/python3.11/site-packages/langchain_core/runnables/passthrough.py", line 415, in invoke
return self._call_with_config(self._invoke, input, config, **kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 1246, in _call_with_config
context.run(
File "//lib/python3.11/site-packages/langchain_core/runnables/config.py", line 326, in call_func_with_variable_args
return func(input, **kwargs) # type: ignore[call-arg]
^^^^^^^^^^^^^^^^^^^^^
File "//lib/python3.11/site-packages/langchain_core/runnables/passthrough.py", line 402, in _invoke
**self.mapper.invoke(
^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2692, in invoke
output = {key: future.result() for key, future in zip(steps, futures)}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2692, in
output = {key: future.result() for key, future in zip(steps, futures)}
^^^^^^^^^^^^^^^
File "/lib/python3.11/concurrent/futures/_base.py", line 456, in result
return self.__get_result()
^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/concurrent/futures/_base.py", line 401, in __get_result
raise self._exception
File "/lib/python3.11/concurrent/futures/thread.py", line 58, in run
result = self.fn(*self.args, **self.kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File “/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2053, in invoke
input = step.invoke(
^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2692, in invoke
output = {key: future.result() for key, future in zip(steps, futures)}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/runnables/base.py", line 2692, in
output = {key: future.result() for key, future in zip(steps, futures)}
^^^^^^^^^^^^^^^
File “/lib/python3.11/concurrent/futures/_base.py", line 449, in result
return self.__get_result()
^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/concurrent/futures/_base.py", line 401, in __get_result
raise self._exception
File "/lib/python3.11/concurrent/futures/thread.py", line 58, in run
result = self.fn(*self.args, **self.kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/retrievers.py", line 121, in invoke
return self.get_relevant_documents(
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/retrievers.py", line 224, in get_relevant_documents
raise e
File "/lib/python3.11/site-packages/langchain_core/retrievers.py", line 217, in get_relevant_documents
result = self._get_relevant_documents(
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_core/vectorstores.py", line 654, in _get_relevant_documents
docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_community/vectorstores/elasticsearch.py", line 632, in similarity_search
results = self._search(
^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_community/vectorstores/elasticsearch.py", line 796, in _search
query_vector = self.embedding.embed_query(query)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/lib/python3.11/site-packages/langchain_community/embeddings/huggingface.py", line 269, in embed_query
text = text.replace("\n", " ")
^^^^^^^^^^^^
AttributeError: 'dict' object has no attribute 'replace'

System Info
python == 3.11.4
langchain == 0.1.7
langchain-community == 0.0.20
elasticsearch == 8.10.0

Replies:5 comments · 4 replies

1315577677
on Feb 20, 2024
The “retriever1” is a dictionary object, and you need to convert it to a string.

3 replies
@mfwz247
mfwz247
on Mar 18, 2024
Hello, Any idea how to do this?

@maximeperrindev
maximeperrindev
on Mar 19, 2024
Hi @mfwz247,

Here is how you can do it :

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

chain = (
       {"context": retriever1 | format_docs, "question": RunnablePassthrough()}
       | rag_prompt
       | llm
       | StrOutputParser()
       )
You need to chain the retriever with a formatting method that will convert the dict to a string.

@pechaut78
pechaut78
on Apr 23, 2024
that does not solve the issue.

you have to write

        def format_docs(d):
            return str(d.input)
and
"context": format_docs | retriever1

But that should not be needed, huggingface.py makes an assumption that should not be made.
It will work with standard invoke call, but not advanced LCEL

This is a bug


cburchett
on May 9, 2024
I am getting the same error. This is definitely a bug in hugginface.py. I couldn't get it to work with @pechaut78 solution or @maximeperrindev solution.

I am using:
langchain==0.1.19
langchain-community==0.0.38

Here is my solution which eliminates the need for from langchain.embeddings.huggingface import HuggingFaceEmbeddings which I found from #7818:

from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from typing import List

class CustomEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return [self.model.encode(d).tolist() for d in documents]

    def embed_query(self, query: str) -> List[float]:
        return self.model.encode([query])[0].tolist()

def get_chain():
    embeddings = CustomEmbeddings(model_name=embeddings_model_name)
    #embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
    chromaClient = chromadb.HttpClient(host=embeddings_server_url)
    db = Chroma(client=chromaClient, collection_name=embeddings_collection, embedding_function=embeddings)

    retriever = db.as_retriever(k=embeddings_top_k)
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))
        | prompt
        | llm
        | StrOutputParser()
    )

    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}
    ).assign(answer=rag_chain_from_docs)

    chain = rag_chain_with_source

    return chain

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def generate_tokens(question):
    for tokens in get_chain().stream({"question": question}):
         yield tokens
I am new to this and still learning so please let me know if you have any feedback on this solution.

1 reply
@gee4vee
gee4vee
on Jul 16, 2024
How do you implement this solution when your Chroma retriever is in a separate node from the node that does the chaining with the prompt and LLM?


cburchett
on Jul 17, 2024
So in my environment, I had Ollama in container, Chroma in a container and my Python code in a 3rd container, and a 4th NextJS container running in Kubernetes. Here is a little more refined version of what I posted previously using an ONNX-based embeddings/encoder model, instead of SentenceTransformer (which I found was very blotted):

   # Create an instance of the MyONNXMiniLM_L6_v2 embeddings model
    embeddings = MyONNXMiniLM_L6_v2(model_path=models_directory)
    
    # Create a Chroma client to connect to the embeddings database
    chromaClient = chromadb.HttpClient(host=embeddings_server_url)
    
    # Create a Chroma instance with the client, collection name, and the embeddings function
    db = Chroma(client=chromaClient, collection_name=embeddings_collection, embedding_function=embeddings)

    # Create a retriever using the embeddings database with k as the number of top embeddings to retrieve
    retriever = db.as_retriever(k=embeddings_top_k)
    
    # Create a RAG chain that consists of multiple runnables
    rag_chain_from_docs = (
        RunnablePassthrough.assign(context=(lambda x: format_docs(x["context"])))  # Assign the formatted context to the 'context' key
        | prompt  # Use the prompt template to generate a prompt
        | llm  # Use the Ollama language model to generate an answer
        | StrOutputParser()  # Parse the output of the language model as a string
    )

    # Create a parallel runnable that runs the retriever and the question in parallel
    rag_chain_with_source = RunnableParallel(
        {"context": retriever, "question": RunnablePassthrough()}  # Assign the retriever and the question to the respective keys
    ).assign(answer=rag_chain_from_docs)
But to answer your question, I used this pip package:
chromadb==0.4.24
with this docker container:
chromadb/chroma:0.5.1.dev84
I then created a Kubernetes clusterIP service to communicated to the Chroma container pod) on port 8000. I put the service reference into a configmap and imported that as a environment variable into my Python container something like this:
embeddings_server_url: http://chatter-chroma-srv.chatter-app.svc.cluster.local:8000
This environment variable is then mapped into the following line:
python chromaClient = chromadb.HttpClient(host=embeddings_server_url)
Then used LangChain's Chroma:
from langchain_community.vectorstores.chroma import Chroma
to use the chromaClient:
 db = Chroma(client=chromaClient, collection_name=embeddings_collection, embedding_function=embeddings).

I was creating a simple RAG application with a NextJS frontend using LangChain, Chroma, and Ollama, running in Kubernetes. You could do this without Kubernetes and whether or whether containers.

0 replies

lharrison13
on Dec 21, 2024
Was an issue ever opened for this? It is still happening in the current version of langchain-huggingface.