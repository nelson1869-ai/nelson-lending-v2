class OutboxItemModel {
  final String id;
  final String eventType;
  final String aggregateType;
  final String aggregateId;
  final String recipientType;
  final String recipientId;
  final String channel;
  final String templateKey;
  final String status;
  final int attemptCount;
  final int maxAttempts;
  final DateTime? nextAttemptAt;
  final DateTime? lastAttemptAt;
  final DateTime? deliveredAt;
  final String? lastError;
  final DateTime createdAt;
  final DateTime updatedAt;

  const OutboxItemModel({
    required this.id,
    required this.eventType,
    required this.aggregateType,
    required this.aggregateId,
    required this.recipientType,
    required this.recipientId,
    required this.channel,
    required this.templateKey,
    required this.status,
    required this.attemptCount,
    required this.maxAttempts,
    this.nextAttemptAt,
    this.lastAttemptAt,
    this.deliveredAt,
    this.lastError,
    required this.createdAt,
    required this.updatedAt,
  });

  factory OutboxItemModel.fromJson(Map<String, dynamic> json) {
    return OutboxItemModel(
      id: json['id'] as String,
      eventType: json['event_type'] as String,
      aggregateType: json['aggregate_type'] as String,
      aggregateId: json['aggregate_id'] as String,
      recipientType: json['recipient_type'] as String,
      recipientId: json['recipient_id'] as String,
      channel: json['channel'] as String,
      templateKey: json['template_key'] as String,
      status: json['status'] as String,
      attemptCount: json['attempt_count'] as int,
      maxAttempts: json['max_attempts'] as int,
      nextAttemptAt: json['next_attempt_at'] != null
          ? DateTime.parse(json['next_attempt_at'] as String)
          : null,
      lastAttemptAt: json['last_attempt_at'] != null
          ? DateTime.parse(json['last_attempt_at'] as String)
          : null,
      deliveredAt: json['delivered_at'] != null
          ? DateTime.parse(json['delivered_at'] as String)
          : null,
      lastError: json['last_error'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  bool get isDeadLetter => status == 'dead_letter';
}

class OutboxListModel {
  final List<OutboxItemModel> items;
  final int totalCount;

  const OutboxListModel({
    required this.items,
    required this.totalCount,
  });

  factory OutboxListModel.fromJson(Map<String, dynamic> json) {
    final list = json['items'] as List<dynamic>;
    return OutboxListModel(
      items: list
          .map((e) => OutboxItemModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCount: json['total_count'] as int,
    );
  }
}
