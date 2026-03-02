import streamlit as st
import requests
import pandas as pd

# CONFIG

API_URL = "https://shl-assessment-recommender-uovg.onrender.com/recommend"

st.set_page_config(page_title="SHL Assessment Recommender", layout="wide")

st.title("SHL Assessment Recommendation System")
st.write("Enter a job description to get 5-10 most relevant individual test solutions. (The first request can take upto 5 minutes as the backend server is in sleep mode, subsequent requests will be faster.)")

# INPUT

query = st.text_area(
    "Enter Job Description / Query",
    height=200
)

# BUTTON

if st.button("Get Recommendations"):

    if not query.strip():
        st.warning("Please enter a valid query.")
    else:
        with st.spinner("Fetching recommendations..."):

            try:
                response = requests.post(
                    API_URL,
                    json={"query": query}
                )

                if response.status_code == 200:

                    data = response.json()
                    results = data.get("recommended_assessments", [])

                    if not results:
                        st.warning("No recommendations found.")
                    else:
                        st.success(f"Showing {len(results)} recommended assessments")

                        table_data = []

                        for item in results:

                            # Handle duration
                            duration = item.get("duration")
                            if duration is None:
                                duration_display = "N/A"
                            else:
                                duration_display = f"{duration} mins"

                            # Expand test types properly
                            test_types = item.get("test_type", [])
                            test_type_display = ", ".join(test_types)

                            # Make URL clickable
                            url = item.get("url")
                            clickable_url = f"[{url}]({url})"

                            table_data.append({
                                "Assessment Name": item.get("name"),
                                "URL": clickable_url,
                                "Test Type": test_type_display,
                                "Duration": duration_display
                            })

                        df = pd.DataFrame(table_data)

                        # Render clickable links properly
                        st.markdown(
                            df.to_markdown(index=False),
                            unsafe_allow_html=True
                        )

                else:
                    st.error(f"API Error: {response.text}")

            except Exception as e:
                st.error(f"Connection error: {str(e)}")