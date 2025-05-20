#!/usr/bin/env python
"""
Script to test if we can list inference profiles from AWS Bedrock.
"""

import boto3
import json
from pprint import pprint

def main():
    print("Testing AWS Bedrock inference profiles...")
    
    # Create Bedrock management client
    bedrock_mgmt = boto3.client("bedrock")
    
    try:
        # List all available inference profiles
        print("\nListing inference profiles:")
        profiles_response = bedrock_mgmt.list_inference_profiles()
        
        if not profiles_response.get("inferenceProfiles"):
            print("No inference profiles found. You may need to create them in the AWS Bedrock console.")
            return
        
        # Print all inference profiles
        print(f"Found {len(profiles_response['inferenceProfiles'])} inference profiles:")
        for profile in profiles_response["inferenceProfiles"]:
            print(f"\nProfile: {profile.get('inferenceProfileName')}")
            print(f"ARN: {profile.get('inferenceProfileArn')}")
            print(f"Model ID: {profile.get('modelId')}")
            print(f"Status: {profile.get('status')}")
        
        # Save the full response to a file for inspection
        with open("inference_profiles.json", "w") as f:
            json.dump(profiles_response, f, indent=2)
        print("\nFull response saved to inference_profiles.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nPossible reasons for this error:")
        print("1. You don't have the necessary permissions to list inference profiles")
        print("2. You haven't created any inference profiles in the AWS Bedrock console")
        print("3. Your AWS credentials are not properly configured")
        print("\nTo create inference profiles:")
        print("1. Go to the AWS Bedrock console")
        print("2. Navigate to 'Inference profiles'")
        print("3. Click 'Create inference profile'")
        print("4. Follow the instructions to create profiles for the models you want to use")

if __name__ == "__main__":
    main()