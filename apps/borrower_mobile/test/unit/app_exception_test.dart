import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:borrower_mobile/core/errors/app_exception.dart';

void main() {
  group('AppException Tests', () {
    test('parseDioException parses 401 response to UnauthorizedException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/borrower/auth/login'),
        response: Response(
          requestOptions: RequestOptions(path: '/api/v1/borrower/auth/login'),
          statusCode: 401,
          data: {'detail': 'Invalid credentials'},
        ),
        type: DioExceptionType.badResponse,
      );

      final exception = parseDioException(dioError);
      expect(exception, isA<UnauthorizedException>());
      expect(exception.message, equals('Invalid credentials'));
    });

    test('parseDioException parses 409 response to ConflictException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/borrower/registrations'),
        response: Response(
          requestOptions:
              RequestOptions(path: '/api/v1/borrower/registrations'),
          statusCode: 409,
          data: {'detail': 'Registration already exists'},
        ),
        type: DioExceptionType.badResponse,
      );

      final exception = parseDioException(dioError);
      expect(exception, isA<ConflictException>());
      expect(exception.message, equals('Registration already exists'));
    });

    test('parseDioException parses 422 response to ValidationException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/api/v1/borrower/registrations'),
        response: Response(
          requestOptions:
              RequestOptions(path: '/api/v1/borrower/registrations'),
          statusCode: 422,
          data: {'detail': 'Invalid phone number'},
        ),
        type: DioExceptionType.badResponse,
      );

      final exception = parseDioException(dioError);
      expect(exception, isA<ValidationException>());
      expect(exception.message, equals('Invalid phone number'));
    });
  });
}
