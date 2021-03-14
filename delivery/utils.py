def get_error_objects(serializer):
    error_objects = []
    for key, value in enumerate(serializer.errors):
        if value:
            serialized_object = serializer.data[key]
            error_objects.append(serialized_object)
    return error_objects
