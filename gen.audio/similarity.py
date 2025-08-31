import os
import re
import time
import math
from collections import Counter
from difflib import SequenceMatcher

def normalize_text(text):
    """Clean and normalize text for comparison"""
    # Remove extra whitespace, punctuation, and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.strip().lower())
    text = re.sub(r'\s+', ' ', text)
    words = [word for word in text.split() if word]
    return words, text

def jaccard_similarity(set1, set2):
    """Calculate Jaccard similarity between two sets"""
    if not set1 and not set2:
        return 1.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two word frequency vectors"""
    if not vec1 or not vec2:
        return 0.0
    
    # Create word frequency vectors
    all_words = set(vec1.keys()).union(set(vec2.keys()))
    vec1_norm = sum(vec1.get(word, 0) ** 2 for word in all_words) ** 0.5
    vec2_norm = sum(vec2.get(word, 0) ** 2 for word in all_words) ** 0.5
    
    if vec1_norm == 0 or vec2_norm == 0:
        return 0.0
    
    dot_product = sum(vec1.get(word, 0) * vec2.get(word, 0) for word in all_words)
    return dot_product / (vec1_norm * vec2_norm)

def word_order_similarity(words1, words2):
    """Calculate word order similarity between two word lists"""
    if not words1 or not words2:
        return 0.0
    
    # Find common words and their positions
    common_words = set(words1).intersection(set(words2))
    if not common_words:
        return 0.0
    
    # Get positions of common words
    pos1 = {word: [i for i, w in enumerate(words1) if w == word] for word in common_words}
    pos2 = {word: [i for i, w in enumerate(words2) if w == word] for word in common_words}
    
    # Calculate position differences
    total_diff = 0
    total_pairs = 0
    
    for word in common_words:
        positions1 = pos1[word]
        positions2 = pos2[word]
        
        # Use minimum number of occurrences
        min_count = min(len(positions1), len(positions2))
        for i in range(min_count):
            diff = abs(positions1[i] - positions2[i])
            total_diff += diff
            total_pairs += 1
    
    if total_pairs == 0:
        return 0.0
    
    # Normalize by text length
    max_len = max(len(words1), len(words2))
    avg_diff = total_diff / total_pairs
    order_similarity = max(0, 1 - (avg_diff / max_len))
    
    return order_similarity

def frequency_similarity(words1, words2):
    """Calculate frequency-based similarity between two word lists"""
    if not words1 and not words2:
        return 1.0
    
    freq1 = Counter(words1)
    freq2 = Counter(words2)
    
    # Calculate intersection and union
    intersection = sum((freq1 & freq2).values())
    union = sum((freq1 | freq2).values())
    
    return intersection / union if union > 0 else 0.0

def compare_text_similarity_advanced(text1, text2, detailed=False):
    """
    Advanced text similarity comparison using multiple algorithms.
    
    Args:
        text1 (str): First text to compare
        text2 (str): Second text to compare
        detailed (bool): Whether to return detailed analysis
    
    Returns:
        float or dict: Similarity score between 0.0 and 1.0, or detailed analysis if detailed=True
    """
    # Clean and normalize texts
    words1, clean_text1 = normalize_text(text1)
    words2, clean_text2 = normalize_text(text2)
    
    # Calculate individual similarity scores
    word_set1 = set(words1)
    word_set2 = set(words2)
    
    jaccard_score = jaccard_similarity(word_set1, word_set2)
    word_freq1 = Counter(words1)
    word_freq2 = Counter(words2)
    cosine_score = cosine_similarity(word_freq1, word_freq2)
    sequence_score = SequenceMatcher(None, clean_text1, clean_text2).ratio()
    order_score = word_order_similarity(words1, words2)
    frequency_score = frequency_similarity(words1, words2)
    
    # Weighted combined score
    combined_score = (
        sequence_score * 0.3 +      # Character-level similarity
        cosine_score * 0.25 +       # Word frequency similarity
        jaccard_score * 0.2 +       # Set-based similarity
        frequency_score * 0.15 +    # Improved frequency similarity
        order_score * 0.1           # Word order similarity
    )
    
    # Ensure the score is between 0.0 and 1.0
    combined_score = max(0.0, min(1.0, combined_score))
    
    if detailed:
        analysis = {
            'combined_score': round(combined_score, 4),
            'individual_scores': {
                'sequence_similarity': round(sequence_score, 4),
                'cosine_similarity': round(cosine_score, 4),
                'jaccard_similarity': round(jaccard_score, 4),
                'frequency_similarity': round(frequency_score, 4),
                'word_order_similarity': round(order_score, 4)
            },
            'text_analysis': {
                'text1_length': len(words1),
                'text2_length': len(words2),
                'common_words': len(word_set1.intersection(word_set2)),
                'unique_words_text1': len(word_set1),
                'unique_words_text2': len(word_set2),
                'word_overlap_ratio': len(word_set1.intersection(word_set2)) / max(len(word_set1), len(word_set2)) if max(len(word_set1), len(word_set2)) > 0 else 0
            }
        }
        return analysis
    
    return round(combined_score, 4)

def compare_text_similarity(text1, text2):
    """
    Simple text similarity comparison - returns combined score only
    """
    return compare_text_similarity_advanced(text1, text2, detailed=False)

def compare_files(file1, file2, detailed=False):
    """
    Compare two text files and return similarity score
    
    Args:
        file1 (str): Path to first text file
        file2 (str): Path to second text file
        detailed (bool): Whether to return detailed analysis
    
    Returns:
        float or dict: Similarity score or detailed analysis
    """
    try:
        with open(file1, 'r', encoding='utf-8') as f:
            text1 = f.read().strip()
        
        with open(file2, 'r', encoding='utf-8') as f:
            text2 = f.read().strip()
        
        return compare_text_similarity_advanced(text1, text2, detailed=detailed)
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return None
    except Exception as e:
        print(f"Error reading files: {e}")
        return None

def get_similarity_quality(score):
    """Get quality assessment based on similarity score"""
    if score >= 0.9:
        return "EXCELLENT"
    elif score >= 0.8:
        return "GOOD"
    elif score >= 0.6:
        return "FAIR"
    else:
        return "POOR"

def main():
    """Main function for standalone similarity comparison"""
    print("Text Similarity Analysis Tool")
    print("=" * 50)
    
    # Check if story.txt and story.str.txt exist for comparison
    original_file = "story.txt"
    transcribed_file = "story.str.txt"
    
    if os.path.exists(original_file) and os.path.exists(transcribed_file):
        print(f"Found files to compare:")
        print(f"  • {original_file}")
        print(f"  • {transcribed_file}")
        print()
        
        start_time = time.time()
        
        # Perform detailed comparison
        result = compare_files(original_file, transcribed_file, detailed=True)
        
        if result:
            print("📊 DETAILED SIMILARITY ANALYSIS")
            print("=" * 50)
            
            # Combined score
            combined_score = result['combined_score']
            quality = get_similarity_quality(combined_score)
            print(f"🎯 Combined Similarity Score: {combined_score:.4f} ({quality})")
            print()
            
            # Individual scores
            print("📈 Individual Algorithm Scores:")
            for algorithm, score in result['individual_scores'].items():
                print(f"  • {algorithm.replace('_', ' ').title()}: {score:.4f}")
            print()
            
            # Text analysis
            analysis = result['text_analysis']
            print("📝 Text Analysis:")
            print(f"  • Original text words: {analysis['text1_length']}")
            print(f"  • Transcribed text words: {analysis['text2_length']}")
            print(f"  • Common words: {analysis['common_words']}")
            print(f"  • Unique words (original): {analysis['unique_words_text1']}")
            print(f"  • Unique words (transcribed): {analysis['unique_words_text2']}")
            print(f"  • Word overlap ratio: {analysis['word_overlap_ratio']:.4f}")
            print()
            
            # Quality assessment
            if combined_score >= 0.9:
                print("🎯 EXCELLENT transcription quality!")
            elif combined_score >= 0.8:
                print("✅ GOOD transcription quality")
            elif combined_score >= 0.6:
                print("⚠️  FAIR transcription quality")
            else:
                print("❌ POOR transcription quality")
            
            end_time = time.time()
            print(f"\n⏱️  Analysis completed in {end_time - start_time:.2f} seconds")
        
    else:
        print("No files found for comparison.")
        print("Expected files:")
        print(f"  • {original_file}")
        print(f"  • {transcribed_file}")
        print()
        print("You can also use the functions directly:")
        print("  • compare_text_similarity(text1, text2)")
        print("  • compare_text_similarity_advanced(text1, text2, detailed=True)")
        print("  • compare_files(file1, file2, detailed=True)")

if __name__ == "__main__":
    main()
