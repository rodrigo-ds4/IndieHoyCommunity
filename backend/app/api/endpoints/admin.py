"""
Admin Endpoints
For development and testing purposes
"""

from fastapi import APIRouter, HTTPException
from app.data.sample_data import create_sample_data, clear_sample_data

router = APIRouter()


@router.post("/create-sample-data")
async def create_test_data():
    """Create sample users and shows for testing the LangChain agent"""
    try:
        create_sample_data()
        return {
            "message": "Sample data created successfully",
            "note": "Check console for details about test scenarios"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-sample-data")
async def clear_test_data():
    """Clear all sample data"""
    try:
        clear_sample_data()
        return {"message": "Sample data cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-scenarios")
async def get_test_scenarios():
    """Get information about available test scenarios"""
    return {
        "test_users": [
            {
                "email": "juan@example.com",
                "scenario": "Valid user - should get discounts",
                "status": "active, fees current, 1/3 monthly discounts used"
            },
            {
                "email": "maria@example.com", 
                "scenario": "Behind on fees - should be rejected",
                "status": "active, fees NOT current"
            },
            {
                "email": "carlos@example.com",
                "scenario": "Inactive subscription - should be rejected", 
                "status": "inactive subscription"
            },
            {
                "email": "ana@example.com",
                "scenario": "New user - should get discounts",
                "status": "active, no previous discounts"
            }
        ],
        "test_shows": [
            {
                "show_id": 1,
                "title": "Rock en Buenos Aires",
                "scenario": "Perfect for discounts - 15 days away",
                "expected": "Should allow discounts"
            },
            {
                "show_id": 2, 
                "title": "Jazz Night",
                "scenario": "Good for discounts - 7 days away",
                "expected": "Should allow discounts"
            },
            {
                "show_id": 3,
                "title": "Folklore Argentino", 
                "scenario": "Too close - 12 hours away",
                "expected": "Should reject (too close to show)"
            },
            {
                "show_id": 4,
                "title": "Tango Milonga",
                "scenario": "Sold out",
                "expected": "Should reject (no tickets available)"
            }
        ],
        "test_request_examples": [
            {
                "user_email": "juan@example.com",
                "show_id": "1", 
                "reason": "Soy estudiante de música y gran fan de Los Piojos",
                "expected_result": "APPROVED - Good user, good reason, valid show"
            },
            {
                "user_email": "maria@example.com",
                "show_id": "1",
                "reason": "Quiero ir al show con mis amigos",
                "expected_result": "REJECTED - User behind on fees"
            },
            {
                "user_email": "juan@example.com",
                "show_id": "3",
                "reason": "Es mi banda favorita",
                "expected_result": "REJECTED - Show too close (< 24 hours)"
            }
        ]
    } 