from openai import OpenAI
import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv

#load .env values
load_dotenv()
client = OpenAI()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

#init session state
if "generated" not in st.session_state:
    st.session_state.generated = False
if "output" not in st.session_state:
    st.session_state.output = ""

#app setup
st.set_page_config(page_title="William's AI Ops Tool", layout="wide")
st.title("⚙️ William’s AI Ops Tool")

#input
input_text = st.text_area("Drop in messy notes, ideas, or updates:", height=300)

#mode selector
output_type = st.selectbox("What do you want to get back?", [
    "TL;DR Summary", 
    "To-Do List", 
    "📅 Calendar Event", 
    "🧠 Automate All"
])

#generate the output
if st.button("Generate Output"):
    with st.spinner("Thinking..."):
        try:
            #build prompt
            if output_type == "TL;DR Summary":
                prompt = f"Turn this into a useful TL;DR / summary I can send to the team, make it in bullet points:\n\n{input_text}"

            elif output_type == "To-Do List":
                prompt = f"Pull out the actual to-dos from this — don’t make stuff up, just list what needs doing in separate lines and don’t have numbers or bullet points:\n\n{input_text}"

            elif output_type == "📅 Calendar Event":
                prompt = f"""Extract all events or meetings that include an explicit **month**, **day**, and **start time** (e.g. \"July 4\", \"10:00 AM\").  

                ✅ Only include events where the date and start time are clearly mentioned.  
                ❌ Do **not** include events with vague or relative time references like \"next week\", \"in 2 days\", \"mid next week\", \"tbd\" or \"before Friday\".

                YOU MUST MUST MUST Format each valid event on a new line like this:

                Event title, Month Day, Start Time – End Time  
                Example: Strategy Sync, July 4, 10:00 AM – 11:00 AM

                DO NOT FORGET THE FORMATTING, YOU MUST PUT IT IN THE FORMAT ABOVE ONLY NO EXCEPTIONS AT ALL!
                If the **end time is not mentioned**, assume the event is **one hour long** and GENERATE the end time as one hour after the start time.
                REMEMBER: YOU MUST INCLUDE END TIME NO MATTER WHAT.
                REMEMBER: Return one event per line. If multiple events happen on the same day, list them separately with their own titles and times.
                Here is the input:
                {input_text}"""

            elif output_type == "🧠 Automate All":
                prompt = f"""You're an AI-powered operations assistant. From the following unstructured input, return valid JSON with:

                {{
                \"tl;dr\": \"- summary point 1\\n- summary point 2\",
                \"todos\": \"action item one\\naction item two\",
                \"calendar\": \"Event title, July 10, 2:00 PM – 3:00 PM\\nAnother event, July 9, 10:00 AM – 11:00 AM\"
                }}

                Your job:
                - Summarise key info clearly (tl;dr)
                - Pull out action items (todos)
                - Extract dated events and format exactly like shown (calendar)

                Only return the JSON. No markdown, no explanation.

                Input:
                {input_text}"""

            #GPT call
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content.strip()

            if output_type == "🧠 Automate All":
                try:
                    parsed = json.loads(content)
                    st.session_state.output = {
                        "tl;dr": parsed.get("tl;dr", ""),
                        "todos": parsed.get("todos", ""),
                        "calendar": parsed.get("calendar", "")
                    }
                except json.JSONDecodeError:
                    st.error("⚠️ Parsing failed. Showing raw output instead.")
                    st.session_state.output = content
            else:
                st.session_state.output = content

            st.session_state.generated = True

        except Exception as e:
            st.error(f"❌ OpenAI error: {e}")
            st.session_state.generated = False

#show output
if st.session_state.generated:
    if output_type == "🧠 Automate All" and isinstance(st.session_state.output, dict):
        st.text_area("📌 TL;DR", value=st.session_state.output.get("tl;dr", ""), height=150)
        st.text_area("✅ To-Dos", value=st.session_state.output.get("todos", ""), height=150)
        st.text_area("📅 Calendar", value=st.session_state.output.get("calendar", ""), height=150)
    else:
        st.text_area("Generated Output", value=st.session_state.output, height=300)

#send to automation
if st.session_state.generated and st.button("Send to Workflow") and N8N_WEBHOOK_URL:
    with st.spinner("Sending to automation..."):
        try:
            if output_type == "🧠 Automate All":
                payload = {
                    "type": "🧠 Automate All",
                    "original": input_text,
                    "result": st.session_state.output
                }
            else:
                payload = {
                    "type": output_type,
                    "original": input_text,
                    "result": st.session_state.output
                }

            res = requests.post(N8N_WEBHOOK_URL, json=payload)
            st.write("🌐 Status code:", res.status_code)

            if res.status_code == 200:
                st.success("✅ Sent to workflow!")
            else:
                st.error(f"❌ Failed to send: {res.status_code} - {res.text}")

        except Exception as e:
            st.error(f"❌ EXCEPTION: {e}")
