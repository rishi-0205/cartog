"""gRPC stub call. PATTERN: RPC-GRPC-01."""
import grpc

channel = grpc.insecure_channel("localhost:50051")

def call_grpc():
    """Call a gRPC method."""
    return channel
