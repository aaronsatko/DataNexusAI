import json
from rich import print
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI


load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-3.5-turbo"

# Load the target dataframe on memory
path = r"backends\data\target_df.csv"
target_df = pd.read_csv(path)

# Function to get the prediction for a specific lyric
async def get_ind_prediction(i, user_prompt_input):
    # Get the lyrics and target
    lyrics_i = target_df["lyrics"].tolist()[i]
    target_i = target_df["target"].tolist()[i]

    # Initialize the client
    client = AsyncOpenAI(api_key=API_KEY)
    prompt_in = user_prompt_input + lyrics_i
    
    model = MODEL
    
    # Get the genre prediction
    completion = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_in}],
        temperature=1
    )
    prediction = completion.choices[0].message.content
    
    # Prepare prompt for scoring
    score_prompt = f"""This is the input predicton from a model. We will extract the genre from the text, and return JSON format. Examine its accuracy whether the prediction is correct or not.
    
    If there is not enough information to, return accuracy "0"
    
    # Target Genre
    {target_i}
    
    # Input From the Model
    {prediction}
    
    
    Examine whether the prediction from the model is matching with the target genre.
    If the prediction is not matching with the target genre, return accuracy "0"
    
    # Output
    {{
        "model_prediction_full_text": "str",
        "target_genre": "str [Hip-Hop,Pop,Country,Rock,R&B-Only one from the model]",
        "predicted_genre": "str",
        "accuracy": "int[0-1]"
    }}
    """
    
    # Get the genre score
    score_completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": score_prompt}],
        temperature=1,
        response_format={"type": "json_object"}
    )
    
    genre_score = score_completion.choices[0].message.content
    json_genre_score = json.loads(genre_score)
    
    return json_genre_score



# Function to get all predictions asynchronously
async def get_all_predictions(user_prompt_input):
    tasks = []
    for i in range(len(target_df)):
        tasks.append(get_ind_prediction(i, user_prompt_input))
    
    predictions = await asyncio.gather(*tasks)
    return predictions


# Create and set a new event loop, then run the coroutine
def run_async_predictions(user_prompt_input):
    return asyncio.run(get_all_predictions(user_prompt_input))


def calculate_accuracy(team_name, user_text):

    res = run_async_predictions(user_text)
    
    try:
        results_df = pd.DataFrame(res)
        results_df['accuracy'] = results_df['accuracy'].astype(int)
        accuracy = float(results_df['accuracy'].mean())
        from datetime import datetime
        updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # json results with team name and accuracy updated time
        json_results = {
            "name": team_name,
            "score": accuracy,
            "last_updated": updated_time
        }
        
        return json_results
    
    except Exception as e:
        print(f"Error calculating accuracy: {e}")
        return None
