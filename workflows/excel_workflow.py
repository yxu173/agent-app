import base64
import pandas as pd
import os
from typing import List, Optional, Dict, Iterator
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.sqlite import SqliteStorage
from agno.workflow import RunResponse, Workflow
from pydantic import BaseModel, Field
from agno.utils.log import logger
from workflows.settings_manager import WorkflowSettingsManager

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

    # Excel Analysis Agent: Analyzes keywords for SEO value
    keyword_analyzer: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
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

    def run(
        self,
        file_path: str,
        niche: str,
        chunk_size: str = "100",
        session_id: Optional[str] = None,
    ) -> Iterator[RunResponse]:
        logger.info(f"Processing Excel file with session_id: {session_id}")

        if self.run_id is None:
            raise ValueError("Run ID is not set")

        # Get the actual session ID from the workflow
        actual_session_id = session_id or self.session_id or 'default'
        logger.info(f"Using session ID: {actual_session_id}")

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

        # Process the Excel file directly
        excel_file_path = self.process_excel_file(file_path, actual_session_id)
        if not excel_file_path:
            yield RunResponse(
                run_id=self.run_id,
                content="Error: Failed to process Excel file",
            )
            return

        # Get file info for progress tracking
        file_info = get_excel_file_info(excel_file_path)
        total_rows = file_info.get('total_rows', 0)
        column_names = file_info.get('column_names', [])

        # Initial progress message
        yield RunResponse(
            run_id=self.run_id,
            content=f"📊 **Excel File Analysis Started**\n\n"
                    f"📁 File: {excel_file_path}\n"
                    f"🎯 Niche: {niche}\n"
                    f"📈 Total Rows: {total_rows}\n"
                    f"📋 Columns: {', '.join(column_names[:5])}{'...' if len(column_names) > 5 else ''}\n"
                    f"🔄 Processing in chunks of {chunk_size_int} rows...\n"
                    f"⏳ Estimated chunks: {(total_rows + chunk_size_int - 1) // chunk_size_int}\n\n"
                    f"---"
        )

        # Process Excel file in chunks
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

            # Extract keywords for display
            keywords_for_display = self.extract_keywords_for_display(chunk_df, start_row, end_row)

            # Show chunk processing start
            yield RunResponse(
                run_id=self.run_id,
                content=f"🔍 **Processing Chunk {chunk_number}**\n\n"
                        f"📊 Position: {current_pos}/{total_rows} rows ({progress_percentage:.1f}%)\n"
                        f"📝 Analyzing {len(keywords_for_display)} keywords from rows {start_row + 1}-{end_row}\n"
                        f"🔄 Remaining chunks: {remaining_chunks}\n\n"
                        f"**Keywords in this chunk:**\n"
                        f"{keywords_for_display}\n\n"
                        f"🤖 AI is analyzing keywords for SEO value in the {niche} niche..."
            )

            # Analyze keywords
            analysis_response: RunResponse = self.keyword_analyzer.run(keywords_text)
            if (
                analysis_response is not None
                and analysis_response.content is not None
                and isinstance(analysis_response.content, ExcelChunkAnalysis)
            ):
                # Save results
                keywords_data = []
                valuable_keywords = []
                for keyword_eval in analysis_response.content.valuable_keywords:
                    keywords_data.append({
                        'keyword': keyword_eval.keyword,
                        'reason': keyword_eval.reason
                    })
                    valuable_keywords.append(keyword_eval.keyword)

                total_keywords += len(keywords_data)
                self.save_keywords_to_session(actual_session_id, keywords_data)

                # Show chunk results
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"✅ **Chunk {chunk_number} Complete**\n\n"
                            f"📊 Position: {current_pos}/{total_rows} rows ({progress_percentage:.1f}%)\n"
                            f"🎯 Valuable keywords found: {len(keywords_data)}\n"
                            f"📈 Total accumulated: {total_keywords} keywords\n"
                            f"🔄 Remaining chunks: {remaining_chunks}\n\n"
                            f"**Valuable keywords from this chunk:**\n"
                            f"{', '.join(valuable_keywords[:10])}{'...' if len(valuable_keywords) > 10 else ''}\n\n"
                            f"**Sample reasons:**\n"
                            f"{self.format_sample_reasons(keywords_data[:3])}\n\n"
                            f"---"
                )

        final_results = self.finalize_session(actual_session_id)
        yield RunResponse(run_id=self.run_id, content=final_results)

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
        """Finalize the session and return summary."""
        try:
            session_id = session_id or 'default'
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            session_keywords = []

            if os.path.exists(session_excel_file):
                try:
                    df = pd.read_excel(session_excel_file)
                    session_keywords = df.to_dict('records')
                except:
                    session_keywords = []

            if session_keywords:
                result = f"🎉 **Session Complete!**\n\n"
                result += f"📊 **Summary:**\n"
                result += f"• Total valuable keywords processed: {len(session_keywords)}\n"
                result += f"• File saved: {session_excel_file}\n"
                result += f"• File size: {self.get_file_size(session_excel_file)} MB\n\n"
                #result += f"📥 **Download your results:**\n"
                #result += f"🔗 {download_url}\n\n"
                result += f"💡 **What's in the file:**\n"
                result += f"• Keyword: The valuable keyword\n"
                result += f"• Reason: Why this keyword was selected as valuable\n\n"
                result += f"✅ Your Excel file is ready for download!"
            else:
                result = "Session complete! No valuable keywords found in this session."

            if session_id:
                self.add_results_to_cache(session_id, result)

            return result

        except Exception as e:
            logger.error(f"Error finalizing session: {e}")
            return f"Error finalizing session: {str(e)}"

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
    return ExcelProcessor(
        workflow_id="excel-keyword-processor",
        user_id=user_id,
        session_id=session_id,
        storage=SqliteStorage(
            table_name="excel_processor_workflows",
            db_file="tmp/excel_processor_agent.db",
            mode="workflow",
            auto_upgrade_schema=True,
        ),
        debug_mode=debug_mode,
    )
