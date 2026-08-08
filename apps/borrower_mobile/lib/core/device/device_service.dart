import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../storage/token_storage_service.dart';

class DeviceService {
  final TokenStorageService _tokenStorage;

  DeviceService({required TokenStorageService tokenStorage})
      : _tokenStorage = tokenStorage;

  /// Returns a persistent stable installation/device identifier for the Borrower application.
  Future<String> getOrCreateDeviceIdentifier() async {
    final existingId = await _tokenStorage.getDeviceIdentifier();
    if (existingId != null && existingId.length >= 16) {
      return existingId;
    }

    final newId = _generateUuidV4();
    await _tokenStorage.saveDeviceIdentifier(newId);
    return newId;
  }

  String _generateUuidV4() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));

    bytes[6] = (bytes[6] & 0x0f) | 0x40; // Version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // Variant 10xx

    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20, 32)}';
  }
}

final deviceServiceProvider = Provider<DeviceService>((ref) {
  final tokenStorage = ref.watch(tokenStorageProvider);
  return DeviceService(tokenStorage: tokenStorage);
});
