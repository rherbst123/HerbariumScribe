from model_factory import get_best_vision_model, create_best_vision_processor

def main():
    # Get the best vision model
    best_model = get_best_vision_model()
    print("Best vision model:")
    print(best_model)
    
    # Create a processor for the best model
    if best_model:
        processor = create_best_vision_processor(
            prompt_name="test",
            prompt_text="Please describe what you see in this image."
        )
        print(f"\nCreated processor: {processor.__class__.__name__}")
        print(f"Model: {processor.model}")
        print(f"Model name: {processor.modelname}")
    else:
        print("\nNo vision models available.")

if __name__ == "__main__":
    main()