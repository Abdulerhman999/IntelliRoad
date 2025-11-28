from google import genai
client = genai.Client(api_key="AIzaSyA26eKSB2-oKWyx4PaxJ_strkvqZkWDnDQ")

def complete_missing(fields):
    prompt = f"Fill missing Pakistan road-project data: {fields}"
    r = client.models.generate(
        model="gemini-1.5-pro",
        contents=prompt
    )
    return r.text