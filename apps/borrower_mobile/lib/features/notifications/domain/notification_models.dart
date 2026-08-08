class BorrowerNotification {
  final String id;
  final String title;
  final String body;
  final String eventType;
  final String sourceId;
  final DateTime? readAt;
  final DateTime createdAt;

  const BorrowerNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.eventType,
    required this.sourceId,
    this.readAt,
    required this.createdAt,
  });

  factory BorrowerNotification.fromJson(Map<String, dynamic> json) {
    return BorrowerNotification(
      id: json['id'] as String,
      title: json['title'] as String,
      body: json['body'] as String,
      eventType: json['event_type'] as String,
      sourceId: json['source_id'] as String,
      readAt: json['read_at'] != null
          ? DateTime.parse(json['read_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  bool get isRead => readAt != null;
}
