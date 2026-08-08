import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/core/errors/app_exception.dart';

void main() {
  group('parseDioException', () {
    test('parses connection timeout to TimeoutException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionTimeout,
      );

      final parsed = parseDioException(dioError);
      expect(parsed, isA<TimeoutException>());
    });

    test('parses connection error to NetworkException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionError,
      );

      final parsed = parseDioException(dioError);
      expect(parsed, isA<NetworkException>());
    });

    test('parses 401 response to UnauthorizedException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/login'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/login'),
          statusCode: 401,
          data: {'detail': 'Invalid credentials'},
        ),
      );

      final parsed = parseDioException(dioError);
      expect(parsed, isA<UnauthorizedException>());
      expect(parsed.message, equals('Invalid credentials'));
    });

    test('parses 422 response to ValidationException', () {
      final dioError = DioException(
        requestOptions: RequestOptions(path: '/login'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/login'),
          statusCode: 422,
          data: {
            'detail': [
              {'msg': 'Field required'}
            ]
          },
        ),
      );

      final parsed = parseDioException(dioError);
      expect(parsed, isA<ValidationException>());
      expect(parsed.message, equals('Field required'));
    });
  });
}
