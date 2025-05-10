import streamlit as st
import os
import json
import logging
from dotenv import load_dotenv
from sseclient import SSEClient

# ------------------------------------------------------------------------------
# Configure Logging
# ------------------------------------------------------------------------------

#streamlit run frontend_demo.py

logging.basicConfig(
    level=logging.DEBUG,  # Change to logging.INFO or logging.ERROR if too verbose
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    st.title("RAG + SSE Demo — Show Only Prompt & Sources")

    # --------------------------------------------------------------------------
    # 1. Load environment variables (Optional, but kept for completeness)
    # --------------------------------------------------------------------------
    load_dotenv()
    logger.debug("Loaded environment variables.")

    # --------------------------------------------------------------------------
    # 2. Initialize session_state variables
    # --------------------------------------------------------------------------
    if "rag_prompt" not in st.session_state:
        st.session_state["rag_prompt"] = None
        logger.debug("Initialized st.session_state['rag_prompt'] to None.")

    if "rag_sources" not in st.session_state:
        st.session_state["rag_sources"] = None
        logger.debug("Initialized st.session_state['rag_sources'] to None.")

    # --------------------------------------------------------------------------
    # 3. Collect user inputs
    # --------------------------------------------------------------------------
    query = st.text_input("Enter your query:", value="What is the UKP LAB?")
    author = st.text_input("Enter your allowed UserGroup:", value="")

    # SSE endpoint (GET-based)
    sse_url = "http://127.0.0.1:8000/retrieve_chunks"
    sse_url = "http://127.0.0.1:4096/retrieve_chunks"

    # --------------------------------------------------------------------------
    # 4. Button to start SSE retrieval
    # --------------------------------------------------------------------------
    if st.button("Send Query"):
        logger.info("Send Query button clicked.")

        # 4a. Reset relevant session state (for a new query)
        st.session_state["rag_prompt"] = None
        st.session_state["rag_sources"] = None

        # Build the GET request URL with query params
        url_with_params = f"{sse_url}?query={query}&jwt_token={author}"
        logger.debug(f"Constructed SSE URL: {url_with_params}")

        # ----------------------------------------------------------------------
        # 4b. Perform SSE call (once) to fetch RAG prompt and sources
        # ----------------------------------------------------------------------
        with st.spinner("Retrieving and reranking chunks via SSE..."):
            logger.info("Starting SSE request to backend...")
            try:
                sse_client = SSEClient(url_with_params)
                for event in sse_client:
                    if not event.data:
                        continue  # skip empty
                    raw_data = event.data.strip()
                    logger.debug(f"Received SSE message: {raw_data}")

                    # Try to parse JSON => final payload
                    try:
                        parsed = json.loads(raw_data)
                        logger.debug(f"Parsed JSON: {parsed}")

                        # If the SSE payload includes 'rag_prompt' and/or 'sources'
                        if "rag_prompt" in parsed or "sources" in parsed:
                            if "rag_prompt" in parsed:
                                st.session_state["rag_prompt"] = parsed["rag_prompt"]
                                logger.info("Final RAG prompt received from SSE.")

                            if "sources" in parsed:
                                st.session_state["rag_sources"] = parsed["sources"]
                                logger.info("Sources received from SSE.")

                            logger.info("Updating session state successfully!")
                            break  # Important: once we have final data, stop listening
                        else:
                            # Partial/unexpected JSON => just display it
                            logger.debug(f"Partial/unexpected JSON SSE: {parsed}")
                            st.write(parsed)
                    except json.JSONDecodeError:
                        # It's a status update (e.g., "Retrieval in progress...")
                        logger.debug(f"Status message SSE: {raw_data}")
                        st.write(raw_data)

                logger.info("Finished reading from SSE (broke out of loop).")

            except Exception as e:
                logger.error(f"Error during SSE retrieval: {e}")
                st.error(f"SSE retrieval error: {e}")

        # ----------------------------------------------------------------------
        # 4c. Display only the RAG prompt (no OpenAI call)
        # ----------------------------------------------------------------------
        if st.session_state["rag_prompt"]:
            st.markdown("### RAG Prompt Received:")
            st.text(st.session_state["rag_prompt"])

    # --------------------------------------------------------------------------
    # 5. Display the sources (if we have them)
    # --------------------------------------------------------------------------
    if st.session_state["rag_sources"]:
        st.markdown("### Sources:")
        st.write(st.session_state["rag_sources"])

    # --------------------------------------------------------------------------
    # 6. Reset button
    # --------------------------------------------------------------------------
    if st.button("Reset"):
        logger.info("User clicked Reset.")
        st.session_state["rag_prompt"] = None
        st.session_state["rag_sources"] = None
        # We'll rely on re-render, no need for st.experimental_rerun().

if __name__ == "__main__":
    main()