#!/usr/bin/env python3
"""
Re-analyze existing workouts to regenerate AI analysis with improved prompts.
Updates existing records without creating duplicates.
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase

# Load environment variables
load_dotenv()

DB_PATH = Path(__file__).parent / 'data' / 'fitness_data.db'

def reanalyze_workouts(start_date: str, end_date: str):
    """
    Re-analyze workouts between start_date and end_date
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    db = WorkoutDatabase()
    analyzer = FitFileAnalyzer()
    
    # Get workout analyses in date range
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Find FIT files in date range
        c.execute('''
            SELECT id, workout_day, workout_title, file_name, fit_data
            FROM fit_files
            WHERE workout_day BETWEEN ? AND ?
            ORDER BY workout_day
        ''', (start_date, end_date))
        
        fit_files = c.fetchall()
        
        if not fit_files:
            print(f"No FIT files found between {start_date} and {end_date}")
            return
        
        print(f"\nFound {len(fit_files)} FIT files to analyze:")
        for fit_file_id, workout_day, workout_title, file_name, _ in fit_files:
            print(f"  - FIT ID {fit_file_id}: {workout_day} - {workout_title}")
        
        print("\nAnalyzing with improved AI prompts...")
        
        for fit_file_id, workout_day, workout_title, file_name, fit_data in fit_files:
            if not fit_data:
                print(f"  ✗ Skipping FIT ID {fit_file_id}: No FIT data stored")
                continue
            
            try:
                print(f"\n  Processing {workout_day} - {workout_title}...")
                
                # FIT data is stored as JSON string of parsed metrics
                import json
                parsed_data = json.loads(fit_data)
                
                # Detect peak efforts from parsed data
                peak_efforts = analyzer._detect_peak_efforts(parsed_data)
                
                # Generate AI analysis from parsed data
                ai_analysis = analyzer._generate_ai_analysis(parsed_data, peak_efforts, None)
                
                if not ai_analysis:
                    print(f"    ✗ Analysis generation failed")
                    continue
                
                analysis_result = {
                    'parsed_data': parsed_data,
                    'peak_efforts': peak_efforts,
                    'ai_analysis': ai_analysis,
                    'analyzed_at': datetime.now().isoformat()
                }
                
                # Check if analysis already exists for this FIT file
                c.execute('SELECT id FROM workout_analyses WHERE fit_file_id = ?', (fit_file_id,))
                existing = c.fetchone()
                
                if existing:
                    # Update existing analysis
                    analysis_id = existing[0]
                    c.execute('''
                        UPDATE workout_analyses
                        SET analysis_text = ?,
                            analysis_data = ?,
                            peak_efforts = ?,
                            analyzed_at = ?,
                            model_used = ?
                        WHERE id = ?
                    ''', (
                        analysis_result.get('ai_analysis', ''),
                        str(analysis_result.get('parsed_data', {})),
                        str(analysis_result.get('peak_efforts', {})),
                        datetime.now().isoformat(),
                        'gemini-2.0-flash-exp',
                        analysis_id
                    ))
                    print(f"    ✓ Updated analysis ID {analysis_id}")
                else:
                    # Create new analysis
                    c.execute('''
                        INSERT INTO workout_analyses 
                        (fit_file_id, analysis_text, analysis_data, peak_efforts, analyzed_at, model_used)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        fit_file_id,
                        analysis_result.get('ai_analysis', ''),
                        str(analysis_result.get('parsed_data', {})),
                        str(analysis_result.get('peak_efforts', {})),
                        datetime.now().isoformat(),
                        'gemini-2.0-flash-exp'
                    ))
                    analysis_id = c.lastrowid
                    print(f"    ✓ Created analysis ID {analysis_id}")
                
                # Extract and show key insights
                ai_text = analysis_result.get('ai_analysis', '')
                if 'Key Performance Insights' in ai_text:
                    insights_section = ai_text.split('Key Performance Insights')[1].split('\n\n')[0]
                    print(f"    ✓ Updated with fresh analysis")
                    print(f"      Insights preview: {insights_section[:100]}...")
                else:
                    print(f"    ✓ Updated (AI analysis: {len(ai_text)} chars)")
                
                # Show peak efforts with HR data
                peak_efforts = analysis_result.get('peak_efforts', {})
                if peak_efforts:
                    print(f"      Peak efforts detected:")
                    for effort_type, data in list(peak_efforts.items())[:3]:
                        hr_info = f", {data.get('avg_hr', 'N/A')} bpm" if data.get('avg_hr') else ''
                        print(f"        - {effort_type}: {data.get('power', 'N/A')}W{hr_info}")
                
            except Exception as e:
                print(f"    ✗ Error: {e}")
                continue
        
        conn.commit()
        print("\n✓ Re-analysis complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    # Re-analyze Monday (Nov 17) through Thursday (Nov 20)
    reanalyze_workouts('2025-11-17', '2025-11-20')
