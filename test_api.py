#!/usr/bin/env python3
"""
Moviroo AI Chatbot - API Test Script
Tests all major endpoints with multilingual examples
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = "test_user_123"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}{text}{Colors.ENDC}")

def test_health_check():
    """Test health endpoint"""
    print_header("1. Testing Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        
        print_info(f"Status: {data['status']}")
        print_info(f"Version: {data['version']}")
        print_info(f"Database: {data['database']}")
        print_info(f"Vector Store: {data['vector_store']['total_vectors']} vectors")
        print_success("Health check passed")
        
        return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_load_dataset():
    """Test loading initial dataset"""
    print_header("2. Loading Initial Dataset")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/load-dataset")
        response.raise_for_status()
        data = response.json()
        
        print_info(f"Entries loaded: {data['entries_loaded']}")
        print_success("Dataset loaded successfully")
        
        return True
    except Exception as e:
        print_error(f"Dataset loading failed: {e}")
        return False

def test_rebuild_index():
    """Test rebuilding vector index"""
    print_header("3. Rebuilding Vector Index")
    
    try:
        print_info("This may take a few moments...")
        response = requests.post(f"{BASE_URL}/admin/rebuild-index")
        response.raise_for_status()
        data = response.json()
        
        print_info(f"Total vectors: {data['total_vectors']}")
        print_info(f"By source: {data['by_source']}")
        print_success("Index rebuilt successfully")
        
        return True
    except Exception as e:
        print_error(f"Index rebuild failed: {e}")
        return False

def test_chat_multilingual():
    """Test chat with multiple languages"""
    print_header("4. Testing Multilingual Chat")
    
    test_messages = [
        ("My payment failed. What should I do?", "en", "English"),
        ("Comment réserver une course?", "fr", "French"),
        ("كيف أحجز رحلة؟", "ar", "Arabic"),
        ("machkel fil payement, chneya nel3ab?", "franco-arabic", "Franco-Arabic"),
        ("The app keeps crashing", "en", "English - Bug Report"),
    ]
    
    results = []
    
    for message, expected_lang, lang_name in test_messages:
        print(f"\n{Colors.BOLD}Testing: {lang_name}{Colors.ENDC}")
        print(f"Message: {message}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "message": message,
                    "user_id": USER_ID
                }
            )
            response.raise_for_status()
            data = response.json()
            
            print_info(f"Detected Language: {data['detected_language']}")
            print_info(f"Detected Category: {data['detected_category']}")
            print_info(f"Confidence: {data['confidence_score']:.2f}")
            print_info(f"Response Time: {data['response_time_ms']}ms")
            print_info(f"Response: {data['response'][:100]}...")
            
            if data['confidence_score'] >= 0.5:
                print_success(f"{lang_name} test passed")
                results.append(True)
            else:
                print_error(f"{lang_name} test - low confidence")
                results.append(False)
                
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print_error(f"{lang_name} test failed: {e}")
            results.append(False)
    
    return all(results)

def test_ticket_workflow():
    """Test ticket creation and management"""
    print_header("5. Testing Ticket Workflow")
    
    try:
        # Create ticket
        print(f"{Colors.BOLD}Creating ticket...{Colors.ENDC}")
        create_response = requests.post(
            f"{BASE_URL}/ticket",
            json={
                "user_id": USER_ID,
                "question": "Driver charged me extra after cancelling the ride",
                "category": "payment",
                "language": "en"
            }
        )
        create_response.raise_for_status()
        ticket_data = create_response.json()
        ticket_id = ticket_data['ticket_id']
        
        print_info(f"Ticket created: {ticket_id}")
        print_info(f"Status: {ticket_data['status']}")
        
        # Get ticket
        print(f"\n{Colors.BOLD}Retrieving ticket...{Colors.ENDC}")
        get_response = requests.get(f"{BASE_URL}/ticket/{ticket_id}")
        get_response.raise_for_status()
        
        print_success("Ticket retrieved successfully")
        
        # Update ticket (simulate admin response)
        print(f"\n{Colors.BOLD}Updating ticket...{Colors.ENDC}")
        update_response = requests.put(
            f"{BASE_URL}/ticket/{ticket_id}",
            json={
                "answer": "We apologize for the inconvenience. The extra charge has been refunded to your account.",
                "status": "resolved",
                "admin_id": "admin_001"
            }
        )
        update_response.raise_for_status()
        
        print_success("Ticket updated and resolved")
        
        # Get user tickets
        print(f"\n{Colors.BOLD}Getting user tickets...{Colors.ENDC}")
        user_tickets_response = requests.get(f"{BASE_URL}/ticket/user/{USER_ID}")
        user_tickets_response.raise_for_status()
        tickets = user_tickets_response.json()
        
        print_info(f"User has {len(tickets)} ticket(s)")
        print_success("Ticket workflow test passed")
        
        return True
        
    except Exception as e:
        print_error(f"Ticket workflow failed: {e}")
        return False

def test_feedback_submission():
    """Test feedback submission"""
    print_header("6. Testing Feedback Submission")
    
    try:
        # Submit positive feedback
        print(f"{Colors.BOLD}Submitting positive feedback...{Colors.ENDC}")
        feedback_response = requests.post(
            f"{BASE_URL}/feedback",
            json={
                "conversation_id": "test_conv_123",
                "rating": 5,
                "feedback_type": "helpful",
                "user_message": "How do I book a ride?",
                "bot_response": "Booking a ride is easy: 1) Open the app...",
                "comment": "Very helpful response!",
                "user_id": USER_ID
            }
        )
        feedback_response.raise_for_status()
        feedback_data = feedback_response.json()
        
        print_info(f"Feedback ID: {feedback_data['id']}")
        print_info(f"Rating: {feedback_data['rating']}")
        print_success("Positive feedback submitted")
        
        # Submit negative feedback
        print(f"\n{Colors.BOLD}Submitting negative feedback...{Colors.ENDC}")
        neg_feedback_response = requests.post(
            f"{BASE_URL}/feedback",
            json={
                "conversation_id": "test_conv_124",
                "rating": 2,
                "feedback_type": "wrong_answer",
                "user_message": "Why was I charged?",
                "bot_response": "I don't have information about that.",
                "comment": "Didn't answer my question",
                "user_id": USER_ID
            }
        )
        neg_feedback_response.raise_for_status()
        
        print_success("Negative feedback submitted")
        
        # Get feedback stats
        print(f"\n{Colors.BOLD}Getting feedback statistics...{Colors.ENDC}")
        stats_response = requests.get(f"{BASE_URL}/feedback/stats")
        stats_response.raise_for_status()
        stats = stats_response.json()
        
        print_info(f"Total feedback: {stats['total_feedback']}")
        print_info(f"Average rating: {stats['average_rating']}")
        print_success("Feedback test passed")
        
        return True
        
    except Exception as e:
        print_error(f"Feedback test failed: {e}")
        return False

def test_system_stats():
    """Test system statistics"""
    print_header("7. Testing System Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/stats")
        response.raise_for_status()
        stats = response.json()
        
        print(f"{Colors.BOLD}Chatbot Stats:{Colors.ENDC}")
        print_info(f"  Model: {stats['chatbot']['embedding_model']}")
        print_info(f"  Vectors: {stats['chatbot']['vector_store']['total_vectors']}")
        print_info(f"  Languages: {', '.join(stats['chatbot']['supported_languages'])}")
        
        print(f"\n{Colors.BOLD}Ticket Stats:{Colors.ENDC}")
        print_info(f"  Total: {stats['tickets']['total_tickets']}")
        print_info(f"  By Status: {stats['tickets']['by_status']}")
        
        print(f"\n{Colors.BOLD}Feedback Stats:{Colors.ENDC}")
        print_info(f"  Total: {stats['feedback']['total_feedback']}")
        print_info(f"  Average Rating: {stats['feedback']['average_rating']}")
        
        print_success("Statistics test passed")
        
        return True
        
    except Exception as e:
        print_error(f"Statistics test failed: {e}")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                  Moviroo AI Chatbot - API Test Suite                         ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    print_info(f"Testing API at: {BASE_URL}")
    print_info(f"User ID: {USER_ID}\n")
    
    # Run tests
    results = {
        "Health Check": test_health_check(),
        "Load Dataset": test_load_dataset(),
        "Rebuild Index": test_rebuild_index(),
        "Multilingual Chat": test_chat_multilingual(),
        "Ticket Workflow": test_ticket_workflow(),
        "Feedback System": test_feedback_submission(),
        "System Statistics": test_system_stats(),
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 All tests passed! The API is working correctly.{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️  Some tests failed. Please check the logs.{Colors.ENDC}")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Test suite error: {e}{Colors.ENDC}\n")
