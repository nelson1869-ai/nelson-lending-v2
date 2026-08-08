/// Safe Owner profile model returned by /me endpoint.
class OwnerProfile {
  final String id;
  final String username;
  final bool isActive;
  final DateTime createdAt;
  final DateTime? lastLoginAt;

  const OwnerProfile({
    required this.id,
    required this.username,
    required this.isActive,
    required this.createdAt,
    this.lastLoginAt,
  });

  factory OwnerProfile.fromJson(Map<String, dynamic> json) {
    return OwnerProfile(
      id: json['id'] as String,
      username: json['username'] as String,
      isActive: json['isActive'] as bool? ?? json['is_active'] as bool? ?? true,
      createdAt: DateTime.parse(json['createdAt'] as String? ?? json['created_at'] as String),
      lastLoginAt: json['lastLoginAt'] != null
          ? DateTime.parse(json['lastLoginAt'] as String)
          : (json['last_login_at'] != null ? DateTime.parse(json['last_login_at'] as String) : null),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'isActive': isActive,
      'createdAt': createdAt.toIso8601String(),
      'lastLoginAt': lastLoginAt?.toIso8601String(),
    };
  }
}
