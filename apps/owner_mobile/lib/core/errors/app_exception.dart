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
  const NetworkException([String message = 'Network connection unavailable. Please check your internet connection.'])
      : super(message);
}

class TimeoutException extends AppException {
  const TimeoutException([String message = 'Request timed out. Please try again.'])
      : super(message);
}

class UnauthorizedException extends AppException {
  const UnauthorizedException([String message = 'Invalid credentials or session expired.', int? statusCode = 401])
      : super(message, statusCode);
}

class ValidationException extends AppException {
  final Map<String, dynamic>? errors;

  const ValidationException([String message = 'Invalid input parameters.', int? statusCode = 422, this.errors])
      : super(message, statusCode);
}

class ServerException extends AppException {
  const ServerException([String message = 'Server error encountered. Please try again later.', int? statusCode = 500])
      : super(message, statusCode);
}

class UnknownException extends AppException {
  const UnknownException([String message = 'An unexpected error occurred.', int? statusCode])
      : super(message, statusCode);
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
          // FastApi validation error list
          final first = detail.first;
          if (first is Map && first.containsKey('msg')) {
            message = first['msg'].toString();
          }
        }
      }

      if (statusCode == 401) {
        return UnauthorizedException(message.isNotEmpty ? message : 'Invalid credentials', statusCode);
      } else if (statusCode == 422) {
        return ValidationException(message.isNotEmpty ? message : 'Validation failed', statusCode);
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
