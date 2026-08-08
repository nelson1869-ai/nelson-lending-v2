import 'package:dio/dio.dart';

abstract class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException(this.message, [this.statusCode]);

  @override
  String toString() => message;
}

class NetworkException extends AppException {
  const NetworkException(
      [super.message = 'Network connection unavailable', super.statusCode]);
}

class ValidationException extends AppException {
  const ValidationException(super.message, [super.statusCode]);
}

class UnauthorizedException extends AppException {
  const UnauthorizedException(
      [super.message = 'Invalid credentials', super.statusCode = 401]);
}

class ConflictException extends AppException {
  const ConflictException(super.message, [super.statusCode = 409]);
}

class ServerException extends AppException {
  const ServerException(
      [super.message = 'Server error occurred', super.statusCode = 500]);
}

AppException parseDioException(DioException e) {
  if (e.type == DioExceptionType.connectionTimeout ||
      e.type == DioExceptionType.receiveTimeout ||
      e.type == DioExceptionType.sendTimeout ||
      e.type == DioExceptionType.connectionError) {
    return const NetworkException();
  }

  final response = e.response;
  if (response != null) {
    final status = response.statusCode;
    String message = 'An error occurred';

    if (response.data is Map<String, dynamic>) {
      final data = response.data as Map<String, dynamic>;
      message =
          data['detail'] as String? ?? data['message'] as String? ?? message;
    }

    if (status == 401) {
      return UnauthorizedException(message, status);
    } else if (status == 409) {
      return ConflictException(message, status);
    } else if (status == 422) {
      return ValidationException(message, status);
    } else if (status != null && status >= 500) {
      return ServerException(message, status);
    }
    return ValidationException(message, status);
  }

  return NetworkException(e.message ?? 'Unexpected network error');
}
