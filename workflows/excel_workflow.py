import base64
import pandas as pd
import os
from typing import List, Optional, Dict, Iterator, Any
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.workflow import RunResponse, Workflow
from pydantic import BaseModel, Field
from agno.utils.log import logger
from workflows.settings_manager import WorkflowSettingsManager
from workflows.excel_session_manager import ExcelSessionManager

current_row_position = 0


def read_excel_chunk_with_calamine(filename: str, chunk_size: int = 100, reset_position: bool = False) -> tuple[
    pd.DataFrame, int, int]:
    """
    Read Excel file using CalamineWorkbook and return a chunk of rows from the CATEGORY sheet

    Args:
        filename (str): Path to Excel file
        chunk_size (int): Number of rows to read per chunk (default: 100)
        reset_position (bool): Whether to reset the global position counter (default: False)

    Returns:
        tuple: (DataFrame chunk, start_row, end_row)
    """
    global current_row_position

    if reset_position:
        current_row_position = 0

    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(filename)

            sheet_names = workbook.sheet_names
            print(f"Available sheets: {sheet_names}")

            if "CATEGORY" not in sheet_names:
                print("CATEGORY sheet not found, trying first available sheet...")
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()

            if sheet_data:
                headers = sheet_data[0]
                data = sheet_data[1:]
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, trying pandas with calamine engine...")
            try:
                df = pd.read_excel(filename, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, trying default engine...")
                df = pd.read_excel(filename, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, trying pandas with calamine engine...")
            try:
                df = pd.read_excel(filename, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, trying default engine...")
                df = pd.read_excel(filename, sheet_name="CATEGORY")

        total_rows = len(df)

        if current_row_position >= total_rows:
            print("Reached end of file")
            return pd.DataFrame(), current_row_position, total_rows

        end_row = min(current_row_position + chunk_size, total_rows)

        chunk_df = df.iloc[current_row_position:end_row].copy()

        start_row = current_row_position
        current_row_position = end_row

        print(f"Read chunk: rows {start_row + 1} to {end_row} (chunk size: {len(chunk_df)})")

        return chunk_df, start_row, end_row

    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        try:
            print("Trying fallback to default pandas engine...")
            df = pd.read_excel(filename, sheet_name="CATEGORY")

            total_rows = len(df)
            print(f"Total rows in CATEGORY sheet: {total_rows}")

            if current_row_position >= total_rows:
                print("Reached end of file")
                return pd.DataFrame(), current_row_position, total_rows

            end_row = min(current_row_position + chunk_size, total_rows)
            chunk_df = df.iloc[current_row_position:end_row].copy()

            start_row = current_row_position
            current_row_position = end_row

            print(f"Read chunk with fallback: rows {start_row + 1} to {end_row} (chunk size: {len(chunk_df)})")

            return chunk_df, start_row, end_row

        except Exception as fallback_error:
            print(f"Fallback also failed: {str(fallback_error)}")
            raise Exception(f"Failed to read Excel file CATEGORY sheet: {str(e)}")


def reset_excel_position():
    """Reset the global Excel row position counter."""
    global current_row_position
    current_row_position = 0
    print("Reset Excel position counter to 0")


def get_current_excel_position() -> int:
    """Get the current Excel row position."""
    global current_row_position
    return current_row_position


def has_more_chunks(excel_file_path: str) -> bool:
    """Check if there are more chunks available in the Excel file CATEGORY sheet."""
    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(excel_file_path)

            sheet_names = workbook.sheet_names
            if "CATEGORY" not in sheet_names:
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()

            if sheet_data:
                headers = sheet_data[0]
                data = sheet_data[1:]
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")

        total_rows = len(df)
        current_pos = get_current_excel_position()

        return current_pos < total_rows
    except Exception as e:
        print(f"Error checking for more chunks: {e}")
        return False


def get_excel_file_info(excel_file_path: str) -> dict:
    """Get information about the Excel file CATEGORY sheet."""
    try:
        try:
            from python_calamine import CalamineWorkbook
            workbook = CalamineWorkbook.from_path(excel_file_path)

            sheet_names = workbook.sheet_names
            print(f"Available sheets: {sheet_names}")

            if "CATEGORY" not in sheet_names:
                print("CATEGORY sheet not found, using first available sheet...")
                sheet_name = sheet_names[0] if sheet_names else "Sheet1"
            else:
                sheet_name = "CATEGORY"

            print(f"Reading sheet: {sheet_name}")
            sheet_data = workbook.get_sheet_by_name(sheet_name).to_python()

            # Convert to DataFrame
            if sheet_data:
                # Use first row as headers
                headers = sheet_data[0]
                data = sheet_data[1:]  # Skip header row
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame()

        except ImportError:
            print("CalamineWorkbook not available, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")
        except Exception as e:
            print(f"CalamineWorkbook failed: {e}, using pandas with calamine engine...")
            try:
                df = pd.read_excel(excel_file_path, engine='calamine', sheet_name="CATEGORY")
            except:
                print("Calamine engine failed, using default engine...")
                df = pd.read_excel(excel_file_path, sheet_name="CATEGORY")

        return {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'column_names': list(df.columns),
            'current_position': get_current_excel_position(),
            'remaining_rows': len(df) - get_current_excel_position()
        }
    except Exception as e:
        print(f"Error getting Excel file info: {e}")
        return {}


class KeywordEvaluation(BaseModel):
    keyword: str = Field(..., description="The keyword being evaluated.")
    reason: str = Field(..., description="The reason for inclusion or exclusion.")


class ExcelChunkAnalysis(BaseModel):
    audience_analysis: str = Field(...,
                                   description="Detailed statement of target audience analysis and relevant characteristics.")
    valuable_keywords: List[KeywordEvaluation] = Field(..., description="List of valuable keywords and reasons.")


class ExcelProcessor(Workflow):
    """Advanced workflow for processing Excel files and analyzing keywords with AI agents."""

    description: str = dedent("""\
    An intelligent Excel processor that analyzes keywords from Excel files using AI agents.
    This workflow processes Excel files in chunks, analyzes keywords for SEO value,
    and accumulates results in session-specific Excel files. The system excels at
    identifying valuable keywords for content creation and SEO optimization.
    """)

    def __init__(self, **kwargs):
        """Initialize the ExcelProcessor and ensure database tables exist."""
        super().__init__(**kwargs)
        # Initialize database tables
        self._init_database()
        # Initialize session manager
        self.session_manager = ExcelSessionManager()
        # Initialize current session ID
        self.current_session_id = None

    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            from db.init_db import init_database
            init_database()
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            # Continue without failing the workflow initialization

    # Excel Analysis Agent: Analyzes keywords for SEO value
    keyword_analyzer: Agent = Agent(
        model=OpenAIChat(id="openai/o4-mini", base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY")),
        debug_mode=True,
        stream=True,
        instructions=dedent("""\
        You are a Seasoned SEO professional specializing in keyword analysis, At the same time you are an expert content creator (these previous two personalities should work in harmony and compatibility), Your task is objectively evaluating keywords for optimal SEO segments, and given complete keyword lists. Choose Keywords that are valuable and useful to readers., as these selected keywords will be used to create informative blog articles.


Ensure that all evaluations are made solely based on the provided criteria without introducing any personal opinions or assumptions.
________________________________________________________________
**The inputs you will get:**
- Keywords: insert keywords
- Category of each keyword: category ( these categories are beneath the given niche.
NICHE IS { niche } FOR ALL KEYWORDS
________________________________________________________________
First: analyze the keywords carefully to understand its context and its intent ( informational - commercial - Navigational - Transactional ), to determine the target audience whether it is (beginners OR intermediates OR experts) for the keywords.
________________________________________________________________
**Now,follow the following criteria to choose the valuable keywords:**
1-Give all Keywords the same level of attention.
*Note:Keywords can be a sentence, a command, or a question. Never base your analysis on this.*

2-As You are a SEO expert, Consider multiple perspectives before applying the criteria to choose valuable Keywords and then apply the following criteria in order to choose the valuable Keywords:
- Keywords must be grammatically and linguistically correct.
- Valuable Keywords provide deep information yet remain accessible to non-specialists.
-Valuable Keywords offer practical solutions or scientific benefits.
- A valuable Keyword is one that can be understood independently, even if presented alone.



3- Also, as you are a content creator,review each keyword to make sure that:
-Is it scalable for in-depth content?
-Does it provide real solutions to the user?
-Does it maintain clarity and coherence in isolation?
-Does it provide useful information rather than superficial information?
- Is it just an informational intention?

4-After that, Cross-reference the keyword against established industry guidelines and case studies to ensure that its value is consistent across various expert perspectives ( SEO expert and content creators ).

5-whether category is (beginners OR intermediates OR experts),You should Exclude any keyword that requires a level above the intermediates level to understand.
________________________________________________________________
**Important instructions and considerations:**
1. Do not include personal opinions regarding the audience 's interests, desires, or perspectives.
Also “Avoid over‐elaboration or speculative reasoning: focus only on the given criteria without philosophical digressions.”
2. Maintain a professional and objective tone throughout the analysis.
3. Strictly follow the provided standards without deviation.
4. Do not make assumptions about a keyword's depth or complexity; treat all keywords equally without any bias to any each.
5. Do not add any extra emphasis or formatting to the keywords.
7. Disregard search volume when evaluating keywords.
8. Ensure that excluded keywords are only listed in the second table, not in the first.
9. Ensure every keyword is evaluated and appears in one of the two tables (none are neglected).
10. Scientific abbreviations are acceptable in both upper and lower case.
11. Keywords that are trivially simple and cannot support in-depth content should be excluded, but if a straightforward keyword can still yield robust, beneficial content, keep it.
12. If two keywords are ≥ 80 % similar, keep the clearer phrasing and the other similar in the excluded table.
12. Exclude any non-English keywords.
________________________________________________________________
**Remember that the two personas ( the SEO expert and expert content creator ), must work in integration and harmony, without any distractions, contradictions, or objections.**
________________________________________________________________
**The outputs must be as following:**
1. Provide a detailed and accurate statement of target audience analysis, audience level of experience or understanding, and any other relevant characteristics.

2.Table 1 consists of 2 columns (the Valuable Keyword | the reason ).


Ensure that the target audience is clearly indicated and justified based on the complexity and content of the keywords.
________________________________________________________________
**Several lists of keywords will be provided in the same chat, so you are required to deal with each list completely independently to avoid confusion or merging or comparing between the lists.**
________________________________________________________________
The instructions are finished, so after analyzing and understanding them well and in a coherent manner, ask for the inputs.
"""),
        response_model=ExcelChunkAnalysis,
        structured_outputs=True,
    )

    def set_model(self, model_id: Optional[str]) -> None:
        """Update the underlying LLM model used by the keyword analyzer."""
        try:
            if model_id is None or not isinstance(model_id, str) or model_id.strip() == "":
                return
            # Prefer OpenRouter if OPENROUTER_API_KEY is set
            openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
            if openrouter_api_key:
                self.keyword_analyzer.model = OpenAIChat(
                    id=model_id,
                    base_url="https://openrouter.ai/api/v1",
                    api_key=openrouter_api_key,
                )
            else:
                # Fallback to default OpenAI provider with given id
                self.keyword_analyzer.model = OpenAIChat(id=model_id)
        except Exception as e:
            logger.warning(f"Failed to set model to '{model_id}': {e}")

    def create_session(
        self,
        session_name: str,
        file_path: str,
        original_filename: str,
        niche: str,
        chunk_size: int,
        user_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> str:
        """
        Create a new Excel workflow session with database persistence.
        
        Args:
            session_name: User-friendly name for the session
            file_path: Path to the uploaded Excel file
            original_filename: Original name of the uploaded file
            niche: Niche/topic for keyword analysis
            chunk_size: Chunk size for processing
            user_id: Optional user ID
            model_id: Optional model ID used for processing
            
        Returns:
            str: Session ID (UUID)
        """
        try:
            session_manager = ExcelSessionManager()
            session_id = session_manager.create_session(
                session_name=session_name,
                file_path=file_path,
                original_filename=original_filename,
                niche=niche,
                chunk_size=chunk_size,
                user_id=user_id,
                model_id=model_id
            )
            
            # Set the session ID in the workflow
            self.session_id = session_id
            logger.info(f"Created Excel session: {session_id} with name: {session_name}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating Excel session: {e}")
            raise

    def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session name.
        
        Args:
            session_name: The session name to look up
            
        Returns:
            Dict with session data or None if not found
        """
        try:
            session_manager = ExcelSessionManager()
            session_data = session_manager.get_session_by_name(session_name)
            
            if session_data:
                # Set the session ID in the workflow
                self.session_id = session_data['session_id']
                logger.info(f"Loaded Excel session: {session_data['session_id']} with name: {session_name}")
            
            return session_data
            
        except Exception as e:
            logger.error(f"Error getting session by name '{session_name}': {e}")
            return None

    def update_session_status(
        self,
        status: str,
        results_file_path: Optional[str] = None,
        total_keywords: Optional[int] = None,
        enhanced_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update session status and related data.
        
        Args:
            status: New status (pending, processing, completed, failed)
            results_file_path: Optional path to results file
            total_keywords: Optional total number of keywords processed
            enhanced_data: Optional enhanced session data for insights
            
        Returns:
            bool: True if update was successful
        """
        if not self.session_id:
            logger.warning("No session ID available for status update")
            return False
        
        try:
            session_manager = ExcelSessionManager()
            return session_manager.update_session_status(
                session_id=self.session_id,
                status=status,
                results_file_path=results_file_path,
                total_keywords=total_keywords,
                enhanced_data=enhanced_data
            )
            
        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            return False

    def run(self, file_path: str, niche: str, chunk_size: str, session_name: str, original_filename: str, user_id: str = "default_user", model_id: str = "openai/o4-mini") -> Iterator[RunResponse]:
        """
        Run the Excel keyword analysis workflow.
        
        Args:
            file_path: Path to the Excel file
            niche: Niche/topic for keyword analysis
            chunk_size: Chunk size for processing
            session_name: User-friendly name for the session
            original_filename: Original name of the uploaded file
            user_id: User ID for session management
            model_id: Model ID for AI processing
            
        Returns:
            Iterator[RunResponse]: Streaming response with workflow progress
        """
        try:
            # Set the model for this workflow run
            self.set_model(model_id)
            
            # Create a new session
            session_id = self.session_manager.create_session(
                session_name=session_name,
                file_path=file_path,
                original_filename=original_filename,
                niche=niche,
                chunk_size=int(chunk_size),
                user_id=user_id,
                model_id=model_id
            )
            
            # Store the session ID for later use
            self.current_session_id = session_id
            
            # Store initial user message
            user_message = f"Processing Excel file: {original_filename} for niche: {niche}"
            self.session_manager.store_workflow_response(session_id, user_message, "user")
            
            # Initial progress message
            initial_message = (
                f"## 🚀 **Starting Excel Keyword Analysis**\n\n"
                f"**📁 File Details:**\n"
                f"• **File Name**: {original_filename}\n"
                f"• **Niche/Topic**: {niche}\n"
                f"• **Processing Strategy**: {chunk_size} rows per chunk\n\n"
                f"**⚙️ Processing Features:**\n"
                f"• **Chunk-based Processing**: Analyzing {chunk_size} rows at a time for optimal performance\n"
                f"• **AI-Powered Analysis**: Using advanced SEO and content creation criteria\n"
                f"• **Quality Filtering**: Identifying only the most valuable keywords\n"
                f"• **Real-time Progress**: Live updates throughout the analysis\n\n"
                f"---"
            )
            
            # Store initial assistant message
            self.session_manager.store_workflow_response(session_id, initial_message, "assistant")
            
            # Yield initial message
            yield RunResponse(content=initial_message)

            # Process Excel file in chunks
            logger.info(f"Processing Excel file with session_id: {session_id}")

            if self.run_id is None:
                raise ValueError("Run ID is not set")

            # Convert chunk_size string to int
            try:
                chunk_size_int = int(chunk_size)
                if chunk_size_int <= 0:
                    chunk_size_int = 100
                    logger.warning(f"Invalid chunk_size '{chunk_size}', using default value of 100")
            except ValueError:
                chunk_size_int = 100
                logger.warning(f"Invalid chunk_size '{chunk_size}', using default value of 100")

            # Update agent instructions with the dynamic niche
            self.keyword_analyzer.instructions = self.get_agent_instructions(niche)

            # Update session status to processing
            self.update_session_status("processing")

            # Process the Excel file directly
            excel_file_path = self.process_excel_file(file_path, session_id)
            if not excel_file_path:
                self.update_session_status("failed")
                yield RunResponse(
                    run_id=self.run_id,
                    content="Error: Failed to process Excel file",
                )
                return

            # Get file info for progress tracking
            file_info = get_excel_file_info(excel_file_path)
            total_rows = file_info.get('total_rows', 0)
            column_names = file_info.get('column_names', [])

            # Initial progress message with enhanced structure
            initial_progress_message = (
                f"## 🚀 **Excel Keyword Analysis Started**\n\n"
                f"### 📁 **File Information**\n\n"
                f"| Property | Value |\n"
                f"|----------|-------|\n"
                f"| **File Path** | `{os.path.basename(excel_file_path)}` |\n"
                f"| **Niche/Topic** | {niche} |\n"
                f"| **Total Rows** | {total_rows} |\n"
                f"| **Columns** | {', '.join(column_names[:5])}{'...' if len(column_names) > 5 else ''} |\n"
                f"| **Chunk Size** | {chunk_size_int} rows |\n"
                f"| **Estimated Chunks** | {(total_rows + chunk_size_int - 1) // chunk_size_int} |\n\n"
                f"### 🔄 **Processing Strategy**\n\n"
                f"• **Chunk-based Processing**: Analyzing {chunk_size_int} rows at a time for optimal performance\n"
                f"• **AI-Powered Analysis**: Using advanced SEO and content creation criteria\n"
                f"• **Quality Filtering**: Identifying only the most valuable keywords\n"
                f"• **Real-time Progress**: Live updates throughout the analysis\n\n"
                f"---"
            )
            
            # Store initial progress message
            self.session_manager.store_workflow_response(session_id, initial_progress_message, "assistant")
            
            yield RunResponse(
                run_id=self.run_id,
                content=initial_progress_message
            )

           
            total_keywords = 0
            chunk_number = 0

            while has_more_chunks(excel_file_path):
                chunk_number += 1
                current_pos = get_current_excel_position()

                # Read chunk
                chunk_df, start_row, end_row = read_excel_chunk_with_calamine(excel_file_path, chunk_size=chunk_size_int)

                if chunk_df.empty:
                    break

                # Calculate progress
                progress_percentage = (current_pos / total_rows * 100) if total_rows > 0 else 0
                remaining_chunks = (total_rows - current_pos + chunk_size_int - 1) // chunk_size_int

                # Prepare keywords for analysis
                keywords_text = self.prepare_keywords_for_analysis(chunk_df, start_row, end_row)
                if not keywords_text:
                    # Skip empty chunks
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"⏭️ **Chunk {chunk_number} Skipped**\n\n"
                                f"📊 Position: {current_pos}/{total_rows} rows ({progress_percentage:.1f}%)\n"
                                f"📝 No valid keywords found in rows {start_row + 1}-{end_row}\n"
                                f"🔄 Remaining chunks: {remaining_chunks}\n\n"
                                f"---"
                    )
                    continue

                
                keywords_for_display = self.extract_keywords_for_display(chunk_df, start_row, end_row)

                
                chunk_start_message = (
                    f"## 🔍 **Processing Chunk {chunk_number}**\n\n"
                    f"### 📊 **Progress Overview**\n\n"
                    f"| Metric | Value |\n"
                    f"|--------|-------|\n"
                    f"| **Current Position** | {current_pos}/{total_rows} rows |\n"
                    f"| **Progress** | {progress_percentage:.1f}% |\n"
                    f"| **Keywords in Chunk** | {len(keywords_for_display)} |\n"
                    f"| **Rows Range** | {start_row + 1}-{end_row} |\n"
                    f"| **Remaining Chunks** | {remaining_chunks} |\n\n"
                    f"### 📝 **Keywords Being Analyzed**\n\n"
                    f"{keywords_for_display}\n\n"
                    f"### 🤖 **AI Analysis Status**\n\n"
                    f"🔄 **Analyzing keywords for SEO value in the {niche} niche...**\n\n"
                    f"*This may take a few moments as the AI evaluates each keyword based on SEO best practices and content creation potential.*"
                )
                
                self.session_manager.store_workflow_response(session_id, chunk_start_message, "assistant")
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=chunk_start_message
                )

                analysis_result = self.keyword_analyzer.run(keywords_text)

                last_response = None
                try:
                    for resp in analysis_result: 
                        last_response = resp
                except TypeError:
                    last_response = analysis_result

                if (
                    last_response is not None
                    and getattr(last_response, "content", None) is not None
                    and isinstance(last_response.content, ExcelChunkAnalysis)
                ):
                    # Save results
                    keywords_data = []
                    valuable_keywords = []
                    for keyword_eval in last_response.content.valuable_keywords:
                        keywords_data.append({
                            'keyword': keyword_eval.keyword,
                            'reason': keyword_eval.reason
                        })
                        valuable_keywords.append(keyword_eval.keyword)

                    total_keywords += len(keywords_data)
                    self.save_keywords_to_session(session_id, keywords_data)

                    # Show chunk results with enhanced structure
                    chunk_complete_message = (
                        f"## ✅ **Chunk {chunk_number} Complete**\n\n"
                        f"### 📊 **Chunk Summary**\n\n"
                        f"| Metric | Value |\n"
                        f"|--------|-------|\n"
                        f"| **Position** | {current_pos}/{total_rows} rows |\n"
                        f"| **Progress** | {progress_percentage:.1f}% |\n"
                        f"| **Valuable Keywords Found** | {len(keywords_data)} |\n"
                        f"| **Total Accumulated** | {total_keywords} |\n"
                        f"| **Remaining Chunks** | {remaining_chunks} |\n\n"
                        f"### 🎯 **Top Valuable Keywords from This Chunk**\n\n"
                        f"{', '.join(valuable_keywords[:10])}{'...' if len(valuable_keywords) > 10 else ''}\n\n"
                        f"### 💡 **Sample Analysis Reasons**\n\n"
                        f"{self.format_sample_reasons(keywords_data[:3])}\n\n"
                        f"### 📈 **Progress Update**\n\n"
                        f"🔄 **{total_keywords} valuable keywords identified so far**\n\n"
                        f"---"
                    )
                    
                    # Store chunk completion message
                    self.session_manager.store_workflow_response(session_id, chunk_complete_message, "assistant")
                    
                    yield RunResponse(
                        run_id=self.run_id,
                        content=chunk_complete_message
                    )

            final_results = self.finalize_session(session_id)
            
            # Store final results message
            self.session_manager.store_workflow_response(session_id, final_results, "assistant")
            
            # Update session status to completed with results
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            if os.path.exists(session_excel_file):
                # Get enhanced data for the session
                enhanced_data = self.get_enhanced_session_data(session_id)
                self.update_session_status(
                    "completed",
                    results_file_path=session_excel_file,
                    total_keywords=total_keywords,
                    enhanced_data=enhanced_data
                )
            else:
                self.update_session_status("completed", total_keywords=total_keywords)
            
            yield RunResponse(run_id=self.run_id, content=final_results)

        except Exception as e:
            logger.error(f"Error in Excel workflow run: {e}", exc_info=True)
            # Update session status to failed
            if hasattr(self, 'current_session_id') and self.current_session_id:
                self.update_session_status("failed")
            
            yield RunResponse(
                run_id=self.run_id if hasattr(self, 'run_id') else None,
                content=f"## ❌ **An Error Occurred**\n\nAn unexpected error occurred during processing: `{str(e)}`\n\nPlease try again or check the application logs for more details."
            )


    def list_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List Excel workflow sessions.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries
        """
        try:
            session_manager = ExcelSessionManager()
            return session_manager.list_user_sessions(user_id=user_id, limit=limit)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    def get_cached_results(self, session_id: str) -> Optional[str]:
        logger.info("Checking if cached results exist")
        return self.session_state.get("excel_results", {}).get(session_id)

    def add_results_to_cache(self, session_id: str, results: str):
        logger.info(f"Saving results for session: {session_id}")
        self.session_state.setdefault("excel_results", {})
        self.session_state["excel_results"][session_id] = results

    def process_excel_file(self, file_path: str, session_id: Optional[str] = None) -> Optional[str]:
        """Process Excel file from file path or base64 string."""
        try:
            if not file_path:
                return None

            # Check if it's a base64 string or a file path
            if file_path.startswith("data:") or file_path.startswith("base64:"):
                # It's a base64 string
                base64_string = file_path.replace("data:", "").replace("base64:", "")
                base64_string = base64_string.strip().replace('\n', '').replace('\r', '')

                if not base64_string:
                    return None

                try:
                    import re
                    if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', base64_string):
                        return None
                except Exception:
                    return None

                try:
                    excel_bytes = base64.b64decode(base64_string)
                except Exception:
                    return None

                if not excel_bytes:
                    return None

                try:
                    excel_signatures = [
                        b'\x50\x4B\x03\x04',
                        b'\xD0\xCF\x11\xE0',
                        b'\x09\x08\x10\x00',
                    ]
                    is_excel_file = any(excel_bytes.startswith(sig) for sig in excel_signatures)
                    if not is_excel_file:
                        return None
                except Exception:
                    pass

                session_id = session_id or 'default'
                excel_file_path = f"tmp/input_excel_{session_id}.xlsx"

                try:
                    os.makedirs("tmp", exist_ok=True)
                except Exception:
                    return None

                try:
                    with open(excel_file_path, 'wb') as f:
                        f.write(excel_bytes)
                except Exception:
                    return None

            else:
                # It's a file path
                excel_file_path = file_path

            if not os.path.exists(excel_file_path):
                return None

            file_size = os.path.getsize(excel_file_path)
            if file_size == 0:
                return None

            reset_excel_position()
            logger.info(f"Reset Excel position counter for new file: {excel_file_path}")

            return excel_file_path

        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            return None

    def prepare_keywords_for_analysis(self, chunk_df: pd.DataFrame, start_row: int, end_row: int) -> Optional[str]:
        """Prepare keywords from DataFrame for analysis."""
        try:
            keyword_column = None
            category_column = None

            for col in chunk_df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['keyword', 'term', 'phrase', 'word']):
                    keyword_column = col
                elif any(cat in col_lower for cat in ['category', 'type', 'class', 'group']):
                    category_column = col

            if not keyword_column:
                keyword_column = chunk_df.columns[0]

            if not category_column:
                category_column = 'category'
                chunk_df[category_column] = 'general'

            keywords_with_category = []
            for _, row in chunk_df.iterrows():
                keyword = str(row[keyword_column]).strip()
                category = str(row[category_column]).strip()
                if keyword and keyword.lower() not in ['nan', 'none', '']:
                    keywords_with_category.append({
                        'keyword': keyword,
                        'category': category
                    })

            if not keywords_with_category:
                return None

            keywords_text = f"Please analyze the following keywords from the Excel file (rows {start_row + 1} to {end_row}):\n\n"
            for item in keywords_with_category:
                keywords_text += f"- Keyword: {item['keyword']}, Category: {item['category']}\n"

            return keywords_text

        except Exception as e:
            logger.error(f"Error preparing keywords for analysis: {e}")
            return None

    def save_keywords_to_session(self, session_id: Optional[str], keywords_data: List[Dict[str, str]]):
        """Save keywords to session-specific Excel file."""
        try:
            session_id = session_id or 'default'
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"

            existing_keywords = []
            if os.path.exists(session_excel_file):
                try:
                    existing_df = pd.read_excel(session_excel_file)
                    existing_keywords = existing_df.to_dict('records')
                except:
                    existing_keywords = []

            existing_keywords.extend(keywords_data)

            if existing_keywords:
                df = pd.DataFrame(existing_keywords)
                df.to_excel(session_excel_file, index=False)

        except Exception as e:
            logger.error(f"Error saving keywords to session: {e}")

    def finalize_session(self, session_id: Optional[str]) -> str:
        """Finalize the session and return an enhanced, structured summary."""
        try:
            session_id = session_id or 'default'
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            session_keywords = []

            if os.path.exists(session_excel_file):
                try:
                    df = pd.read_excel(session_excel_file)
                    session_keywords = df.to_dict('records')
                except Exception as e:
                    logger.warning(f"Could not read session Excel file '{session_excel_file}': {e}")
                    session_keywords = []

            if session_keywords:
                # Enhanced structured result
                result = f"🎉 **Excel Keyword Analysis Complete!**\n\n"
                
                # Summary section
                result += f"## 📊 **Analysis Summary**\n\n"
                result += f"| Metric | Value |\n"
                result += f"|--------|-------|\n"
                result += f"| **Total Keywords Analyzed** | {len(session_keywords)} |\n"
                result += f"| **File Size** | {self.get_file_size(session_excel_file)} MB |\n"
                result += f"| **Processing Status** | ✅ Complete |\n"
                result += f"| **Results File** | `{os.path.basename(session_excel_file)}` |\n\n"
                
                # Top keywords section as a table for better formatting
                result += f"## 🎯 **Top 10 Valuable Keywords & Analysis**\n\n"
                result += f"| # | Keyword | Reason for Selection |\n"
                result += f"|---|---------|----------------------|\n"
                top_keywords = session_keywords[:10]
                for i, item in enumerate(top_keywords, 1):
                    keyword = item['keyword']
                    reason = str(item.get('reason', '')).replace('\n', ' ').replace('|', ' ') # Sanitize for table
                    reason = reason[:100] + "..." if len(reason) > 100 else reason
                    result += f"| **{i}** | `{keyword}` | *{reason}* |\n"

                if len(session_keywords) > 10:
                    result += f"\n*... and {len(session_keywords) - 10} more valuable keywords are available in the downloadable Excel file.*\n\n"
                
                # Keyword Insights section
                keyword_categories = self.analyze_keyword_categories(session_keywords)
                if keyword_categories:
                    result += f"## 💡 **Keyword Insights**\n\n"
                    result += f"Your keyword list has been analyzed and categorized based on user intent:\n\n"
                    result += f"| Category | Count | Description |\n"
                    result += f"|----------|-------|-------------|\n"
                    if 'question_keywords' in keyword_categories:
                        result += f"| **Question-Based** | {keyword_categories.get('question_keywords', 0)} | Keywords phrased as questions (who, what, why, etc.) |\n"
                    if 'comparison_keywords' in keyword_categories:
                        result += f"| **Comparison** | {keyword_categories.get('comparison_keywords', 0)} | Keywords comparing products or services (best, top, vs) |\n"
                    if 'benefit_keywords' in keyword_categories:
                        result += f"| **Benefit-Oriented** | {keyword_categories.get('benefit_keywords', 0)} | Keywords focused on advantages and benefits |\n"
                    if 'how_to_keywords' in keyword_categories:
                        result += f"| **How-To/Guides** | {keyword_categories.get('how_to_keywords', 0)} | Keywords that suggest instructional content |\n"
                    if 'general_keywords' in keyword_categories:
                        result += f"| **General Informational** | {keyword_categories.get('general_keywords', 0)} | Broad topics for general articles |\n"
                    result += "\n*This can help you plan different types of content to meet user needs.*\n\n"

                # Final success message
                result += f"✅ **Your keyword analysis is ready!** Download the Excel file to access all valuable keywords.\n\n"
                
                # Save enhanced data to session
                self.save_enhanced_session_data(session_id, session_keywords, session_excel_file)
                
            else:
                result = "## ⚠️ **Analysis Complete**\n\n"
                result += "No valuable keywords were found in this session. This could be due to:\n\n"
                result += "• Keywords not meeting the AI's quality criteria\n"
                result += "• The provided Excel file being empty or having an unsupported format\n"
                result += "• Incorrect column names (the tool looks for a 'Keyword' column)\n\n"
                result += "**Recommendation:** Please check your Excel file and try again, or adjust the AI instructions in the sidebar for different results."

            if session_id:
                self.add_results_to_cache(session_id, result)

            return result

        except Exception as e:
            logger.error(f"Error finalizing session: {e}", exc_info=True)
            return f"## ❌ **An Error Occurred**\n\nAn unexpected error occurred while finalizing the session: `{str(e)}`\n\nPlease try again or check the application logs for more details."

    def save_enhanced_session_data(self, session_id: str, keywords_data: List[Dict[str, str]], excel_file_path: str):
        """Save enhanced session data for better user experience."""
        try:
            # Create enhanced session data
            enhanced_data = {
                'session_id': session_id,
                'total_keywords': len(keywords_data),
                'file_path': excel_file_path,
                'file_name': os.path.basename(excel_file_path),
                'file_size_mb': self.get_file_size(excel_file_path),
                'top_keywords': keywords_data[:10],  # Top 10 keywords
                'keyword_categories': self.analyze_keyword_categories(keywords_data),
                'processing_summary': {
                    'status': 'completed',
                    'total_processed': len(keywords_data),
                    'completion_time': pd.Timestamp.now().isoformat()
                }
            }
            
            # Save to session cache
            self.session_state.setdefault("enhanced_session_data", {})
            self.session_state["enhanced_session_data"][session_id] = enhanced_data
            
            logger.info(f"Enhanced session data saved for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving enhanced session data: {e}")

    def analyze_keyword_categories(self, keywords_data: List[Dict[str, str]]) -> Dict[str, int]:
        """Analyze keyword categories for insights."""
        try:
            categories = {}
            for item in keywords_data:
                keyword = item['keyword'].lower()
                
                # Simple category detection based on keyword patterns
                if any(word in keyword for word in ['how', 'what', 'why', 'when', 'where']):
                    categories['question_keywords'] = categories.get('question_keywords', 0) + 1
                elif any(word in keyword for word in ['best', 'top', 'review', 'compare']):
                    categories['comparison_keywords'] = categories.get('comparison_keywords', 0) + 1
                elif any(word in keyword for word in ['benefits', 'advantages', 'pros', 'effects']):
                    categories['benefit_keywords'] = categories.get('benefit_keywords', 0) + 1
                elif any(word in keyword for word in ['recipe', 'how to', 'tutorial', 'guide']):
                    categories['how_to_keywords'] = categories.get('how_to_keywords', 0) + 1
                else:
                    categories['general_keywords'] = categories.get('general_keywords', 0) + 1
            
            return categories
        except Exception as e:
            logger.error(f"Error analyzing keyword categories: {e}")
            return {}

    def get_enhanced_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get enhanced session data from cache."""
        try:
            return self.session_state.get("enhanced_session_data", {}).get(session_id)
        except Exception as e:
            logger.error(f"Error getting enhanced session data: {e}")
            return None

    def get_workflow_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """Get workflow responses for a session."""
        try:
            if hasattr(self, 'session_manager'):
                return self.session_manager.get_workflow_responses(session_id)
            return []
        except Exception as e:
            logger.error(f"Error getting workflow responses: {e}")
            return []

    def clear_workflow_responses(self, session_id: str) -> bool:
        """Clear workflow responses for a session."""
        try:
            if hasattr(self, 'session_manager'):
                return self.session_manager.clear_workflow_responses(session_id)
            return False
        except Exception as e:
            logger.error(f"Error clearing workflow responses: {e}")
            return False

    def get_download_url(self, session_id: str) -> str:
        """Generate download URL based on environment."""
        try:
            from api.settings import api_settings
            base_url = api_settings.get_base_url()
        except ImportError:
            # Fallback if API settings are not available
            import os
            is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"
            if is_development:
                base_url = "http://localhost:8000"
            else:
                base_url = os.getenv("PRODUCTION_URL", "https://your-domain.com")

        return f"{base_url}/v1/downloads/excel/{session_id}"

    def get_file_size(self, file_path: str) -> str:
        """Get file size in MB."""
        try:
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                size_mb = size_bytes / (1024 * 1024)
                return f"{size_mb:.2f}"
            return "0.00"
        except Exception:
            return "0.00"

    def extract_keywords_for_display(self, chunk_df: pd.DataFrame, start_row: int, end_row: int) -> str:
        """Extract and format keywords for display."""
        try:
            keyword_column = None
            category_column = None

            for col in chunk_df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['keyword', 'term', 'phrase', 'word']):
                    keyword_column = col
                elif any(cat in col_lower for cat in ['category', 'type', 'class', 'group']):
                    category_column = col

            if not keyword_column:
                keyword_column = chunk_df.columns[0]

            keywords_with_category = []
            for _, row in chunk_df.iterrows():
                keyword = str(row[keyword_column]).strip()
                category = str(row[category_column]).strip() if category_column else 'general'
                if keyword and keyword.lower() not in ['nan', 'none', '']:
                    keywords_with_category.append({
                        'keyword': keyword,
                        'category': category
                    })

            if keywords_with_category:
                display_lines = []
                for i, item in enumerate(keywords_with_category[:15]):
                    display_lines.append(f"• {item['keyword']} ({item['category']})")

                if len(keywords_with_category) > 15:
                    display_lines.append(f"... and {len(keywords_with_category) - 15} more")

                return '\n'.join(display_lines)
            else:
                return "No valid keywords found in this chunk."

        except Exception as e:
            logger.error(f"Error extracting keywords for display: {e}")
            return "Error extracting keywords for display."

    def format_sample_reasons(self, keywords_data: List[Dict[str, str]]) -> str:
        """Format sample reasons for display."""
        if not keywords_data:
            return "No reasons available."

        formatted_reasons = []
        for item in keywords_data:
            reason = item['reason'][:100] + "..." if len(item['reason']) > 100 else item['reason']
            formatted_reasons.append(f"• **{item['keyword']}**: {reason}")

        return '\n'.join(formatted_reasons)

    def get_agent_instructions(self, niche: str) -> str:
        """Generate agent instructions with dynamic niche and configurable settings."""
        # Get custom instructions from database, fallback to default if not found
        custom_instructions = WorkflowSettingsManager.get_setting(
            workflow_name="excel_processor",
            setting_key="agent_instructions",
            default_value=self._get_default_instructions()
        )
        
        # Replace the niche placeholder in the custom instructions
        return custom_instructions.replace("{niche}", niche)
    
    def _get_default_instructions(self) -> str:
        """Get the default agent instructions."""
        return dedent("""\
            You are a Seasoned SEO professional specializing in keyword analysis, At the same time you are an expert content creator (these previous two personalities should work in harmony and compatibility), Your task is objectively evaluating keywords for optimal SEO segments, and given complete keyword lists. Choose Keywords that are valuable and useful to readers., as these selected keywords will be used to create informative blog articles.


Ensure that all evaluations are made solely based on the provided criteria without introducing any personal opinions or assumptions.
________________________________________________________________
**The inputs you will get:**
- Keywords: insert keywords
- Category of each keyword: category ( these categories are beneath the given niche.
NICHE IS {niche} FOR ALL KEYWORDS
________________________________________________________________
First: analyze the keywords carefully to understand its context and its intent ( informational - commercial - Navigational - Transactional ), to determine the target audience whether it is (beginners OR intermediates OR experts) for the keywords.
________________________________________________________________
**Now,follow the following criteria to choose the valuable keywords:**
1-Give all Keywords the same level of attention.
*Note:Keywords can be a sentence, a command, or a question. Never base your analysis on this.*

2-As You are a SEO expert, Consider multiple perspectives before applying the criteria to choose valuable Keywords and then apply the following criteria in order to choose the valuable Keywords:
- Keywords must be grammatically and linguistically correct.
- Valuable Keywords provide deep information yet remain accessible to non-specialists.
-Valuable Keywords offer practical solutions or scientific benefits.
- A valuable Keyword is one that can be understood independently, even if presented alone.



3- Also, as you are a content creator,review each keyword to make sure that:
-Is it scalable for in-depth content?
-Does it provide real solutions to the user?
-Does it maintain clarity and coherence in isolation?
-Does it provide useful information rather than superficial information?
- Is it just an informational intention?

4-After that, Cross-reference the keyword against established industry guidelines and case studies to ensure that its value is consistent across various expert perspectives ( SEO expert and content creators ).

5-whether category is (beginners OR intermediates OR experts),You should Exclude any keyword that requires a level above the intermediates level to understand.
________________________________________________________________
**Important instructions and considerations:**
1. Do not include personal opinions regarding the audience 's interests, desires, or perspectives.
Also "Avoid over‐elaboration or speculative reasoning: focus only on the given criteria without philosophical digressions."
2. Maintain a professional and objective tone throughout the analysis.
3. Strictly follow the provided standards without deviation.
4. Do not make assumptions about a keyword's depth or complexity; treat all keywords equally without any bias to any each.
5. Do not add any extra emphasis or formatting to the keywords.
7. Disregard search volume when evaluating keywords.
8. Ensure that excluded keywords are only listed in the second table, not in the first.
9. Ensure every keyword is evaluated and appears in one of the two tables (none are neglected).
10. Scientific abbreviations are acceptable in both upper and lower case.
11. Keywords that are trivially simple and cannot support in-depth content should be excluded, but if a straightforward keyword can still yield robust, beneficial content, keep it.
12. If two keywords are ≥ 80 % similar, keep the clearer phrasing and the other similar in the excluded table.
12. Exclude any non-English keywords.
________________________________________________________________
**Remember that the two personas ( the SEO expert and expert content creator ), must work in integration and harmony, without any distractions, contradictions, or objections.**
________________________________________________________________
**The outputs must be as following:**
1. Provide a detailed and accurate statement of target audience analysis, audience level of experience or understanding, and any other relevant characteristics.

2.Table 1 consists of 2 columns (the Valuable Keyword | the reason ).


Ensure that the target audience is clearly indicated and justified based on the complexity and content of the keywords.
________________________________________________________________
**Several lists of keywords will be provided in the same chat, so you are required to deal with each list completely independently to avoid confusion or merging or comparing between the lists.**
________________________________________________________________
The instructions are finished, so after analyzing and understanding them well and in a coherent manner, ask for the inputs.
""")


def get_excel_processor(
    user_id: Optional[str] = None,
    model_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True
) -> ExcelProcessor:
    workflow = ExcelProcessor(
        workflow_id="excel-keyword-processor",
        user_id=user_id,
        session_id=session_id,
        storage=SqliteStorage(
            table_name="excel_processor_workflows",
            db_file="tmp/agent_app.db",
            mode="workflow",
            auto_upgrade_schema=True,
        ),
        debug_mode=debug_mode,
    )
    try:
        # Apply selected model if provided
        workflow.set_model(model_id)
    except Exception:
        pass
    return workflow
