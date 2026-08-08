import 'package:dio/dio.dart';

/// Normalized application exceptions for user-facing UI and error handling.
abstract class AppException implements Exception {
  final String message;
  final int? statusCode;

  const AppException(this.message, [this.statusCode]);

  @override
  String toString() => message;
}

class NetworkException extends AppException {
  const NetworkException(
      [super.message =
          'Network connection unavailable. Please check your internet connection.']);
}

class TimeoutException extends AppException {
  const TimeoutException(
      [super.message = 'Request timed out. Please try again.']);
}

class UnauthorizedException extends AppException {
  const UnauthorizedException(
      [super.message = 'Invalid credentials or session expired.',
      super.statusCode = 401]);
}

class ValidationException extends AppException {
  final Map<String, dynamic>? errors;

  const ValidationException(
      [super.message = 'Invalid input parameters.',
      super.statusCode = 422,
      this.errors]);
}

class ServerException extends AppException {
  const ServerException(
      [super.message = 'Server error encountered. Please try again later.',
      super.statusCode = 500]);
}

class UnknownException extends AppException {
  const UnknownException(
      [super.message = 'An unexpected error occurred.', super.statusCode]);
}

/// Utility for converting raw DioExceptions into safe normalized AppExceptions.
AppException parseDioException(DioException error) {
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
      return const TimeoutException();

    case DioExceptionType.connectionError:
      return const NetworkException();

    case DioExceptionType.badResponse:
      final statusCode = error.response?.statusCode;
      final data = error.response?.data;
      String message = 'Request failed';

      if (data is Map<String, dynamic> && data.containsKey('detail')) {
        final detail = data['detail'];
        if (detail is String) {
          message = detail;
        } else if (detail is List && detail.isNotEmpty) {
          final first = detail.first;
          if (first is Map && first.containsKey('msg')) {
            message = first['msg'].toString();
          }
        }
      }

      if (statusCode == 401) {
        return UnauthorizedException(
            message.isNotEmpty ? message : 'Invalid credentials', statusCode);
      } else if (statusCode == 422) {
        return ValidationException(
            message.isNotEmpty ? message : 'Validation failed', statusCode);
      } else if (statusCode != null && statusCode >= 500) {
        return ServerException('Server error ($statusCode)', statusCode);
      }
      return UnknownException(message, statusCode);

    case DioExceptionType.cancel:
      return const UnknownException('Request was cancelled.');

    default:
      return UnknownException(error.message ?? 'An unexpected error occurred.');
  }
}
