# 📱 Flutter Integration Guide - Moviroo AI Chatbot

Complete guide for integrating the AI chatbot backend with your Flutter mobile app.

## 🎯 Overview

This guide shows you how to:
1. Set up HTTP client in Flutter
2. Integrate chat functionality
3. Handle tickets and feedback
4. Manage conversations
5. Handle multilingual support

## 📦 Flutter Dependencies

Add to your `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.2
  uuid: ^4.3.3
  provider: ^6.1.1  # For state management
  flutter_dotenv: ^5.1.0  # For environment variables
```

## 🔧 Configuration

Create `lib/config/api_config.dart`:

```dart
class ApiConfig {
  // Change this to your production API URL
  static const String baseUrl = 'http://localhost:8000';
  
  // API Endpoints
  static const String chatEndpoint = '/chat';
  static const String ticketEndpoint = '/ticket';
  static const String feedbackEndpoint = '/feedback';
  static const String healthEndpoint = '/health';
  
  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
```

## 📡 API Service Layer

Create `lib/services/chatbot_service.dart`:

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../config/api_config.dart';
import '../models/chat_models.dart';

class ChatbotService {
  final http.Client _client = http.Client();
  String? _conversationId;
  String? _userId;

  // Initialize service with user ID
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _userId = prefs.getString('user_id');
    
    if (_userId == null) {
      // Generate new user ID if not exists
      _userId = const Uuid().v4();
      await prefs.setString('user_id', _userId!);
    }
    
    _conversationId = prefs.getString('conversation_id');
  }

  // Send chat message
  Future<ChatResponse> sendMessage(String message) async {
    try {
      await initialize();

      final response = await _client
          .post(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.chatEndpoint}'),
            headers: {
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'message': message,
              'user_id': _userId,
              'conversation_id': _conversationId,
            }),
          )
          .timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Save conversation ID for continuity
        _conversationId = data['conversation_id'];
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('conversation_id', _conversationId!);
        
        return ChatResponse.fromJson(data);
      } else {
        throw Exception('Failed to send message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error sending message: $e');
    }
  }

  // Create support ticket
  Future<Ticket> createTicket({
    required String question,
    String? category,
    String? language,
  }) async {
    try {
      await initialize();

      final response = await _client
          .post(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketEndpoint}'),
            headers: {
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'user_id': _userId,
              'question': question,
              'category': category,
              'language': language ?? 'en',
            }),
          )
          .timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 201) {
        return Ticket.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to create ticket: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error creating ticket: $e');
    }
  }

  // Get user's tickets
  Future<List<Ticket>> getUserTickets({int limit = 10}) async {
    try {
      await initialize();

      final response = await _client
          .get(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.ticketEndpoint}/user/$_userId?limit=$limit'),
            headers: {
              'Content-Type': 'application/json',
            },
          )
          .timeout(ApiConfig.receiveTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((json) => Ticket.fromJson(json)).toList();
      } else {
        throw Exception('Failed to get tickets: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error getting tickets: $e');
    }
  }

  // Submit feedback
  Future<void> submitFeedback({
    required int rating,
    required String feedbackType,
    required String userMessage,
    required String botResponse,
    String? comment,
  }) async {
    try {
      await initialize();

      final response = await _client
          .post(
            Uri.parse('${ApiConfig.baseUrl}${ApiConfig.feedbackEndpoint}'),
            headers: {
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'conversation_id': _conversationId ?? const Uuid().v4(),
              'rating': rating,
              'feedback_type': feedbackType,
              'user_message': userMessage,
              'bot_response': botResponse,
              'comment': comment,
              'user_id': _userId,
            }),
          )
          .timeout(ApiConfig.receiveTimeout);

      if (response.statusCode != 201) {
        throw Exception('Failed to submit feedback: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error submitting feedback: $e');
    }
  }

  // End conversation
  Future<void> endConversation({int? satisfaction}) async {
    try {
      if (_conversationId == null) return;

      final uri = satisfaction != null
          ? Uri.parse(
              '${ApiConfig.baseUrl}${ApiConfig.chatEndpoint}/conversation/$_conversationId?user_satisfaction=$satisfaction')
          : Uri.parse(
              '${ApiConfig.baseUrl}${ApiConfig.chatEndpoint}/conversation/$_conversationId');

      await _client.delete(uri).timeout(ApiConfig.receiveTimeout);

      // Clear conversation
      _conversationId = null;
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('conversation_id');
    } catch (e) {
      throw Exception('Error ending conversation: $e');
    }
  }

  // Check API health
  Future<bool> checkHealth() async {
    try {
      final response = await _client
          .get(Uri.parse('${ApiConfig.baseUrl}${ApiConfig.healthEndpoint}'))
          .timeout(Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  void dispose() {
    _client.close();
  }
}
```

## 📋 Data Models

Create `lib/models/chat_models.dart`:

```dart
class ChatResponse {
  final String response;
  final double confidenceScore;
  final String detectedLanguage;
  final String? detectedCategory;
  final String matchedSource;
  final int? matchedId;
  final int responseTimeMs;
  final String conversationId;
  final String timestamp;
  final List<String>? suggestions;
  final List<Alternative>? alternatives;

  ChatResponse({
    required this.response,
    required this.confidenceScore,
    required this.detectedLanguage,
    this.detectedCategory,
    required this.matchedSource,
    this.matchedId,
    required this.responseTimeMs,
    required this.conversationId,
    required this.timestamp,
    this.suggestions,
    this.alternatives,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      response: json['response'],
      confidenceScore: json['confidence_score'].toDouble(),
      detectedLanguage: json['detected_language'],
      detectedCategory: json['detected_category'],
      matchedSource: json['matched_source'],
      matchedId: json['matched_id'],
      responseTimeMs: json['response_time_ms'],
      conversationId: json['conversation_id'],
      timestamp: json['timestamp'],
      suggestions: json['suggestions'] != null
          ? List<String>.from(json['suggestions'])
          : null,
      alternatives: json['alternatives'] != null
          ? (json['alternatives'] as List)
              .map((a) => Alternative.fromJson(a))
              .toList()
          : null,
    );
  }
}

class Alternative {
  final String answer;
  final double score;
  final String? category;

  Alternative({
    required this.answer,
    required this.score,
    this.category,
  });

  factory Alternative.fromJson(Map<String, dynamic> json) {
    return Alternative(
      answer: json['answer'],
      score: json['score'].toDouble(),
      category: json['category'],
    );
  }
}

class Ticket {
  final int id;
  final String ticketId;
  final String userId;
  final String question;
  final String? answer;
  final String? category;
  final String language;
  final String status;
  final String priority;
  final String createdAt;
  final String? updatedAt;
  final String? resolvedAt;
  final int? resolutionTimeMinutes;

  Ticket({
    required this.id,
    required this.ticketId,
    required this.userId,
    required this.question,
    this.answer,
    this.category,
    required this.language,
    required this.status,
    required this.priority,
    required this.createdAt,
    this.updatedAt,
    this.resolvedAt,
    this.resolutionTimeMinutes,
  });

  factory Ticket.fromJson(Map<String, dynamic> json) {
    return Ticket(
      id: json['id'],
      ticketId: json['ticket_id'],
      userId: json['user_id'],
      question: json['question'],
      answer: json['answer'],
      category: json['category'],
      language: json['language'],
      status: json['status'],
      priority: json['priority'],
      createdAt: json['created_at'],
      updatedAt: json['updated_at'],
      resolvedAt: json['resolved_at'],
      resolutionTimeMinutes: json['resolution_time_minutes'],
    );
  }

  bool get isResolved => status == 'resolved' || status == 'closed';
  bool get isOpen => status == 'open';
}

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final double? confidence;
  final String? category;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.confidence,
    this.category,
  });
}
```

## 🎨 Chat UI Widget

Create `lib/widgets/chat_screen.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/chatbot_service.dart';
import '../models/chat_models.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({Key? key}) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ChatbotService _chatService = ChatbotService();
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _addBotMessage('Hello! How can I help you today?');
  }

  void _addBotMessage(String text, {double? confidence, String? category}) {
    setState(() {
      _messages.add(ChatMessage(
        text: text,
        isUser: false,
        timestamp: DateTime.now(),
        confidence: confidence,
        category: category,
      ));
    });
    _scrollToBottom();
  }

  void _addUserMessage(String text) {
    setState(() {
      _messages.add(ChatMessage(
        text: text,
        isUser: true,
        timestamp: DateTime.now(),
      ));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    _addUserMessage(text);
    _messageController.clear();

    setState(() {
      _isLoading = true;
    });

    try {
      final response = await _chatService.sendMessage(text);
      
      _addBotMessage(
        response.response,
        confidence: response.confidenceScore,
        category: response.detectedCategory,
      );

      // Show suggestions if confidence is low
      if (response.suggestions != null && response.suggestions!.isNotEmpty) {
        _showSuggestions(response.suggestions!);
      }

      // Offer to create ticket if confidence is very low
      if (response.confidenceScore < 0.5) {
        _offerTicketCreation(text);
      }

    } catch (e) {
      _addBotMessage('Sorry, I encountered an error. Please try again.');
      print('Error: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _showSuggestions(List<String> suggestions) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Suggestions'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: suggestions
              .map((s) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text('• $s'),
                  ))
              .toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _offerTicketCreation(String question) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Need More Help?'),
        content: const Text(
          'I couldn\'t find a good answer. Would you like to create a support ticket?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('No, thanks'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              _createTicket(question);
            },
            child: const Text('Create Ticket'),
          ),
        ],
      ),
    );
  }

  Future<void> _createTicket(String question) async {
    try {
      final ticket = await _chatService.createTicket(question: question);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ticket created: ${ticket.ticketId}'),
            backgroundColor: Colors.green,
          ),
        );
        
        _addBotMessage(
          'I\'ve created a support ticket (${ticket.ticketId}) for you. Our team will respond soon!',
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to create ticket'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Moviroo Support'),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              // Show app info
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return _buildMessageBubble(message);
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: Row(
                children: [
                  SizedBox(width: 16),
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 8),
                  Text('Thinking...'),
                ],
              ),
            ),
          _buildMessageInput(),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: message.isUser 
              ? Colors.blue[600] 
              : Colors.grey[300],
          borderRadius: BorderRadius.circular(20),
        ),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.text,
              style: TextStyle(
                color: message.isUser ? Colors.white : Colors.black87,
                fontSize: 15,
              ),
            ),
            if (message.confidence != null && message.confidence! < 0.7)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'Confidence: ${(message.confidence! * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(
                    fontSize: 11,
                    color: Colors.black54,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageInput() {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              decoration: const InputDecoration(
                hintText: 'Type your message...',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 10,
                ),
              ),
              maxLines: null,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.send),
            color: Colors.blue,
            onPressed: _isLoading ? null : _sendMessage,
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _chatService.dispose();
    super.dispose();
  }
}
```

## 🎯 Usage Examples

### 1. Simple Chat Integration

```dart
import 'package:flutter/material.dart';
import 'widgets/chat_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Moviroo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const ChatScreen(),
    );
  }
}
```

### 2. Create Ticket Programmatically

```dart
final chatService = ChatbotService();

try {
  final ticket = await chatService.createTicket(
    question: 'Driver charged me extra after cancellation',
    category: 'payment',
    language: 'en',
  );
  
  print('Ticket created: ${ticket.ticketId}');
} catch (e) {
  print('Error: $e');
}
```

### 3. Submit Feedback

```dart
await chatService.submitFeedback(
  rating: 5,
  feedbackType: 'helpful',
  userMessage: 'How do I book a ride?',
  botResponse: 'Booking a ride is easy...',
  comment: 'Very helpful!',
);
```

### 4. View User Tickets

```dart
final tickets = await chatService.getUserTickets(limit: 10);

for (var ticket in tickets) {
  print('${ticket.ticketId}: ${ticket.status}');
}
```

## 🌍 Multilingual Support

The backend automatically detects language. Just send messages in any supported language:

```dart
// English
await chatService.sendMessage('My payment failed');

// French
await chatService.sendMessage('Mon paiement a échoué');

// Arabic
await chatService.sendMessage('فشل الدفع');

// Franco-Arabic
await chatService.sendMessage('machkel fil payement');
```

## 🎨 UI Customization

Customize the chat appearance in `chat_screen.dart`:

```dart
// Message bubble colors
color: message.isUser 
    ? Colors.blue[600]      // User message color
    : Colors.grey[300],     // Bot message color

// Font sizes
fontSize: 15,               // Message text
fontSize: 11,               // Confidence score

// Bubble styling
borderRadius: BorderRadius.circular(20),
```

## 🔔 Push Notifications (Optional)

To notify users when tickets are resolved:

```dart
// Add to your notification handler
void handleTicketUpdate(Map<String, dynamic> data) {
  final ticketId = data['ticket_id'];
  final status = data['status'];
  
  if (status == 'resolved') {
    showNotification(
      title: 'Ticket Resolved',
      body: 'Your support ticket $ticketId has been resolved!',
    );
  }
}
```

## ⚡ Performance Tips

1. **Cache responses** for common questions
2. **Show typing indicator** while waiting
3. **Implement retry logic** for network failures
4. **Use connection pooling** for HTTP client
5. **Lazy load ticket history** (pagination)

## 🐛 Error Handling

```dart
try {
  final response = await chatService.sendMessage(message);
  // Handle success
} on SocketException {
  // No internet connection
  showError('No internet connection');
} on TimeoutException {
  // Request timeout
  showError('Request timed out');
} catch (e) {
  // Other errors
  showError('Something went wrong');
}
```

## 🧪 Testing

Test the integration:

```dart
void main() {
  testWidgets('Chat sends message', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: ChatScreen()));
    
    // Enter text
    await tester.enterText(
      find.byType(TextField),
      'How do I book a ride?',
    );
    
    // Tap send
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump();
    
    // Verify message appears
    expect(find.text('How do I book a ride?'), findsOneWidget);
  });
}
```

## 📚 Next Steps

1. **Customize UI** to match your app's design
2. **Add error handling** for edge cases
3. **Implement caching** for better performance
4. **Add analytics** to track usage
5. **Test thoroughly** in different scenarios

## 🆘 Troubleshooting

**Issue**: Connection refused
- Solution: Make sure backend is running and URL is correct

**Issue**: Slow responses
- Solution: Check network connection and server load

**Issue**: Parsing errors
- Solution: Verify API response format matches models

---

**Your Flutter app is now ready to integrate with the AI chatbot!** 🎉
