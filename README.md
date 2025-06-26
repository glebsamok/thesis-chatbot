# Thesis Chatbot Project

An AI-powered interview chatbot system for assessing interpersonal traits through conversational interactions. This project combines natural language processing, database management, and machine learning to create an intelligent interviewing system.

## Project Overview

This system is designed to conduct structured interviews and assess four key interpersonal traits:
- **Emotional Intelligence (EI)**: Recognizing and appropriately expressing emotions
- **Perspective Taking (PT)**: Understanding others' viewpoints and motivations
- **Learning Orientation (LO)**: Seeking feedback and learning from experiences
- **Social Curiosity (SC)**: Interest in people and expanding social networks

## Project Structure

### Core Application Files

#### `chatbot_interface.py`
**Purpose**: Main Streamlit web interface for the chatbot application
- Provides interactive chat interface for user interactions
- Manages session state and user persistence
- Handles real-time conversation flow with reactions and follow-ups
- Supports URL parameter-based user identification
- Features modern UI with custom styling

#### `chat_manager.py`
**Purpose**: Central coordinator for chatbot conversation management
- Manages database connections and operations
- Processes user answers and validates against acceptance criteria
- Tracks conversation states and question progression
- Handles subquestion generation with depth limits
- Coordinates with Question class for answer validation

#### `question_init.py`
**Purpose**: Question management and validation system
- Defines the Question class for interview questions
- Handles acceptance criteria validation using OpenAI API
- Generates follow-up questions when answers don't meet criteria
- Creates contextual reactions to user responses
- Manages conversation history retrieval from database

#### `database.py`
**Purpose**: Database initialization and management
- Creates PostgreSQL database schema with three main tables:
  - `questions_and_acceptance`: Stores interview questions and criteria
  - `results`: Stores user responses and conversation data
  - `states_intro`: Stores introductory messages for different states
- Provides functions for dropping tables (development/testing)
- Uses environment variables for database configuration

#### `llm_text_generation.py`
**Purpose**: OpenAI API integration for text generation
- Provides functions for structured JSON responses (`generate_text_json`)
- Handles free-form text generation (`generate_text`)
- Supports both development (env vars) and production (Streamlit secrets) configurations
- Used for acceptance checking, follow-up generation, and answer reactions

#### `utils.py`
**Purpose**: Common utility functions
- `get_file_content()`: Reads and returns file contents as strings
- Used for loading prompts, configurations, and other text files

#### `uuid_gen.py`
**Purpose**: UUID generation utility
- `generate_uuid()`: Creates version 4 UUIDs for unique identification
- Used for generating user IDs and session identifiers

### Data Processing Files

#### `chat_bot_merge.py`
**Purpose**: Data merging and preprocessing script
- Merges chatbot conversation data with external dataset information
- Processes question-answer pairs from chatbot interactions
- Formats data for trait classification analysis
- Exports processed data to JSONL format for downstream analysis
- Handles user ID mapping and data consolidation

### Model Training and Validation Files

#### `finetuning.py`
**Purpose**: Fine-tuning data preparation script
- Processes datasets of questions and answers with trait labels
- Uses GPT-4 to generate reasoning explanations for classifications
- Creates structured training data for model fine-tuning
- Handles error cases and parsing issues
- Outputs dataset with reasoning explanations

#### `job_run.py`
**Purpose**: Model training and prediction script
- Handles training data preparation and formatting
- Creates stratified train/validation splits
- Provides prediction functionality using fine-tuned models
- Configurable system prompts and question columns
- Generates JSONL files for training

#### `validation.py`
**Purpose**: Model validation and evaluation script
- Evaluates fine-tuned model performance on validation data
- Calculates accuracy, classification reports, and confusion matrices
- Implements few-shot learning for improved predictions
- Provides comprehensive evaluation metrics for each trait
- Compares predictions against true labels

#### `new_validation.py`
**Purpose**: Enhanced validation with Pydantic models
- Uses Pydantic for structured output validation
- Implements beta chat completions parse feature
- Provides comprehensive trait definitions and behavioral cues
- Ensures balanced few-shot example selection
- Generates structured reasoning and prediction outputs

#### `chatbot_valid.py`
**Purpose**: Real-world chatbot data validation
- Validates fine-tuned model on actual chatbot conversations
- Processes real user interactions from the chatbot interface
- Compares predictions against true labels from external datasets
- Uses Pydantic models for structured prediction
- Exports results for further analysis

## Database Schema

### Tables

1. **questions_and_acceptance**
   - `question_id` (INTEGER PRIMARY KEY)
   - `question` (TEXT)
   - `acceptance_criteria` (TEXT)
   - `state` (INTEGER)
   - `created_at` (TIMESTAMP)

2. **results**
   - `answer_id` (UUID PRIMARY KEY)
   - `answer_content` (TEXT)
   - `related_question_id` (INTEGER, FOREIGN KEY)
   - `user_id` (TEXT)
   - `state` (INTEGER)
   - `created_at` (TIMESTAMP)

3. **states_intro**
   - `msg_id` (UUID PRIMARY KEY)
   - `state` (INTEGER)
   - `intro_message` (TEXT)

## Key Features

### Conversation Management
- **Adaptive Questioning**: System generates follow-up questions when answers don't meet acceptance criteria
- **State Tracking**: Maintains conversation state and progression through interview phases
- **Depth Control**: Limits subquestion depth to prevent infinite loops
- **Context Awareness**: Uses conversation history for personalized interactions

### AI Integration
- **OpenAI GPT Models**: Uses GPT-4 for natural language processing tasks
- **Fine-tuned Models**: Custom models trained for trait classification
- **Structured Output**: Pydantic models ensure consistent and validated responses
- **Few-shot Learning**: Improves prediction quality with relevant examples

### Data Processing
- **Real-time Processing**: Handles live user interactions
- **Batch Processing**: Processes historical data for model training
- **Data Validation**: Ensures data quality and consistency
- **Export Capabilities**: Generates various output formats for analysis

## Setup and Configuration

### Prerequisites
- Python 3.8+
- PostgreSQL database
- OpenAI API key
- Required Python packages (see requirements.txt)

### Environment Variables
```bash
PG_NAME=your_database_name
PG_USER=your_username
PG_PASS=your_password
PG_HOST=localhost
PG_PORT=XXX
OPENAI_API_KEY=your_openai_api_key
```

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up PostgreSQL database
4. Configure environment variables
5. Initialize database: `python database.py`
6. Run the chatbot: `streamlit run chatbot_interface.py`

## Usage

### Starting the Chatbot
```bash
streamlit run chatbot_interface.py
```

### Data Processing
```bash
python chat_bot_merge.py  # Merge and process data
python finetuning.py      # Prepare training data
python job_run.py         # Train and predict
python validation.py      # Evaluate model performance
```

## File Dependencies

```
chatbot_interface.py
├── chat_manager.py
│   ├── question_init.py
│   │   ├── utils.py
│   │   └── llm_text_generation.py
│   └── database.py
└── uuid_gen.py

Data Processing Pipeline:
chat_bot_merge.py → finetuning.py → job_run.py → validation.py
```

## Model Architecture

The system uses a multi-stage approach:
1. **Conversation Collection**: Real-time user interactions via Streamlit interface
2. **Data Processing**: Merging and formatting conversation data
3. **Model Training**: Fine-tuning GPT models on labeled data
4. **Validation**: Evaluating model performance on test data
5. **Deployment**: Using fine-tuned models for real-time predictions

## Contributing

This is a thesis research project. For questions or collaboration, please contact the author.

## License

This project is part of academic research. Please respect intellectual property rights.

